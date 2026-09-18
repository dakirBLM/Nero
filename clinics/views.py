
from datetime import date, datetime, timedelta
import os
import logging
import json
import secrets
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
logger = logging.getLogger("django")
from django.conf import settings
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Avg
from django.contrib.auth import login
from django.core.files.storage import FileSystemStorage
from django.views.decorators.http import require_POST
from django.urls import reverse
from accounts.forms import UserCreationForm
from patients.models import Patient, MedicalRecord
from .forms import AppointmentForm, ClinicSignUpForm, ClinicGalleryForm, ClinicServiceForm, ClinicUpdateForm
from .models import Appointment, Clinic, ClinicGallery, ClinicService
from posts.models import Post

# Import Review from the new reviews app
from reviews.models import Review


GOOGLE_OAUTH_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_OAUTH_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'


def _google_calendar_client_id():
    return (getattr(settings, 'GOOGLE_CALENDAR_CLIENT_ID', '') or '').strip()


def _google_calendar_client_secret():
    return (getattr(settings, 'GOOGLE_CALENDAR_CLIENT_SECRET', '') or '').strip()


def _google_calendar_redirect_uri(request):
    base = (getattr(settings, 'GOOGLE_CALENDAR_REDIRECT_BASE', '') or '').strip().rstrip('/')
    path = reverse('clinic_google_calendar_callback')
    if base:
        return f"{base}{path}"
    return request.build_absolute_uri(path)


def _google_calendar_exchange_code(code, redirect_uri):
    payload = {
        'code': code,
        'client_id': _google_calendar_client_id(),
        'client_secret': _google_calendar_client_secret(),
        'redirect_uri': redirect_uri,
        'grant_type': 'authorization_code',
    }
    req = Request(
        GOOGLE_OAUTH_TOKEN_URL,
        data=urlencode(payload).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _google_calendar_refresh_token(refresh_token):
    payload = {
        'refresh_token': refresh_token,
        'client_id': _google_calendar_client_id(),
        'client_secret': _google_calendar_client_secret(),
        'grant_type': 'refresh_token',
    }
    req = Request(
        GOOGLE_OAUTH_TOKEN_URL,
        data=urlencode(payload).encode('utf-8'),
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _save_google_calendar_token(request, token_payload):
    if not token_payload:
        return
    existing = request.session.get('google_calendar_token', {})
    access_token = token_payload.get('access_token') or existing.get('access_token')
    refresh_token = token_payload.get('refresh_token') or existing.get('refresh_token')
    expires_in = int(token_payload.get('expires_in') or existing.get('expires_in') or 3600)
    request.session['google_calendar_token'] = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'expires_in': expires_in,
        'updated_at': int(timezone.now().timestamp()),
    }
    request.session.modified = True


def _google_calendar_create_event(access_token, event_payload, calendar_id='primary'):
    endpoint = f"https://www.googleapis.com/calendar/v3/calendars/{quote(calendar_id, safe='')}/events"
    req = Request(
        endpoint,
        data=json.dumps(event_payload).encode('utf-8'),
        headers={
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
        },
        method='POST',
    )
    with urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode('utf-8'))


def _google_http_error_message(exc):
    try:
        raw = exc.read().decode('utf-8')
    except Exception:
        return ''
    try:
        payload = json.loads(raw)
        err = payload.get('error')
        if isinstance(err, dict):
            return err.get('message') or err.get('error_description') or raw
        if isinstance(err, str):
            return err
    except Exception:
        pass
    return raw


def _build_google_calendar_event_payload(clinic, appointment):
    start_date = appointment.treatment_start_date or appointment.appointment_date
    end_date = appointment.treatment_end_date or start_date
    if not start_date:
        return None
    if end_date and end_date < start_date:
        end_date = start_date

    patient_name = (getattr(appointment.patient, 'full_name', '') or 'Patient').strip()
    treatment_service = (appointment.requested_service or '').strip()
    notes = (appointment.notes or '').strip()
    location = ', '.join([part for part in [clinic.full_address, clinic.city, clinic.country] if part])

    details = [
        f'Clinic: {clinic.clinic_name}',
        f'Patient: {patient_name}',
    ]
    if treatment_service:
        details.append(f'Requested service: {treatment_service}')
    if notes:
        details.append(f'Notes: {notes}')

    return {
        'summary': f'Upcoming appointment - {patient_name}',
        'location': location,
        'description': '\n'.join(details),
        'start': {'date': start_date.isoformat()},
        # Google Calendar all-day end date is exclusive.
        'end': {'date': (end_date + timedelta(days=1)).isoformat()},
    }

# Clinic dashboard view (restored)
@login_required
def clinic_dashboard_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    clinic = Clinic.objects.filter(user=request.user).first()
    if clinic is None:
        messages.info(request, 'Please complete your clinic profile to continue.')
        return redirect('clinic_signup')
    assigned_patients = Appointment.objects.filter(clinic=clinic).select_related('patient')
    # Build a deduplicated list of assignments keyed by patient so each patient appears once
    ordered_assignments = assigned_patients.order_by('-created_at')
    unique_assignments_map = {}
    for appt in ordered_assignments:
        pid = getattr(appt, 'patient_id', None)
        if pid and pid not in unique_assignments_map:
            unique_assignments_map[pid] = appt
    # Keep only up to 5 unique patient assignments for dashboard display
    assigned_patients_unique = list(unique_assignments_map.values())[:5]
    appointments = Appointment.objects.filter(clinic=clinic)
    total_appointments = appointments.count()
    pending_appointments = appointments.filter(status='pending').count()
    accepted_appointments = appointments.filter(status='accepted').count()
    recent_appointments = appointments.select_related('patient', 'medical_record').order_by('-created_at')[:5]
    total_patients = assigned_patients.count()
    # Build lists of patients who have had any appointments with this clinic.
    # We don't care about booking status — include patients from any appointment.
    # Build patient lists.
    # Active Patients: 3 random patients whose MedicalRecord.address matches this clinic (city or full address).
    try:
        matching_patient_ids = list(MedicalRecord.objects.filter(
            Q(address__icontains=clinic.city) | Q(address__iexact=clinic.full_address)
        ).values_list('patient_id', flat=True).distinct())
    except Exception:
        matching_patient_ids = []

    if matching_patient_ids:
        active_patients = list(Patient.objects.filter(id__in=matching_patient_ids).order_by('?')[:3])
    else:
        active_patients = []

    # Community Members: 3 random patients who had an accepted booking with this clinic.
    try:
        booked_patient_ids = list(Appointment.objects.filter(clinic=clinic, status='accepted').values_list('patient_id', flat=True).distinct())
    except Exception:
        booked_patient_ids = []

    if booked_patient_ids:
        community_patients = list(Patient.objects.filter(id__in=booked_patient_ids).order_by('?')[:3])
    else:
        community_patients = []
    pending_requests = assigned_patients.filter(status='pending').count()
    # ===== Community patients: show up to 3 most-recent distinct patients with accepted appointments =====
    community_patients = community_patients[:3]
    post_error = None
    if request.method == 'POST' and 'post_content' in request.POST:
        description = request.POST.get('post_content', '').strip()
        image = request.FILES.get('post_image')
        video = request.FILES.get('post_video')
        if description:
            post = Post.objects.create(
                clinic=clinic,
                author=request.user,
                description=description,
                image=image if image else None,
                video=video if video else None
            )
            messages.success(request, 'Post created successfully!')
            return redirect('clinic_dashboard')
        else:
            post_error = 'Please write something to post.'
    # Show all posts site-wide in the clinic dashboard 'All Posts' section
    posts = Post.objects.all().order_by('-created_at')
    # Posts authored by the clinic user (ensure we show only posts from this clinic account)
    clinic_posts = Post.objects.filter(author=clinic.user).order_by('-created_at')
    my_posts = posts.filter(author=request.user)
    if request.method == 'POST' and 'image' in request.FILES:
        gallery_form = ClinicGalleryForm(request.POST, request.FILES)
        if gallery_form.is_valid():
            gallery_item = gallery_form.save(commit=False)
            gallery_item.clinic = clinic
            gallery_item.save()
            messages.success(request, 'Image added to gallery!')
            return redirect('clinic_dashboard')
    if request.method == 'POST' and 'service_name' in request.POST:
        service_form = ClinicServiceForm(request.POST, request.FILES)
        if service_form.is_valid():
            service = service_form.save(commit=False)
            service.clinic = clinic
            service.save()
            messages.success(request, 'Service added!')
            return redirect('clinic_dashboard')
    gallery_form = ClinicGalleryForm()
    service_form = ClinicServiceForm()
    gallery_images = ClinicGallery.objects.filter(clinic=clinic)
    services = ClinicService.objects.filter(clinic=clinic)
    # Reviews summary for sidebar rating
    try:
        reviews = Review.objects.filter(clinic=clinic)
        reviews_count = reviews.count()
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        if reviews_count == 0:
            display_rating = 3.0
        else:
            display_rating = round(avg_rating, 1) if avg_rating is not None else 3.0
    except Exception:
        reviews_count = 0
        display_rating = 3.0
    context = {
        'clinic': clinic,
        'assigned_patients': assigned_patients,
        'assigned_patients_unique': assigned_patients_unique,
        'total_patients': total_patients,
        'active_patients': active_patients,
        'pending_requests': pending_requests,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'accepted_appointments': accepted_appointments,
        'recent_appointments': recent_appointments,
        'gallery_form': gallery_form,
        'service_form': service_form,
        'gallery_images': gallery_images,
        'services': services,
        'display_rating': display_rating,
        'reviews_count': reviews_count,
        'posts': posts,
        'clinic_posts': clinic_posts,
        'my_posts': my_posts,
        'post_error': post_error,
        'community_patients': community_patients,
    }
    return render(request, 'clinics/clinic_dashboard.html', context)
# Clinic signup view (restored)
def clinic_signup_view(request):
    from allauth.socialaccount.models import SocialAccount
    from accounts.views import _get_google_login_url
    from django.urls import reverse

    def _has_google_social(user):
        qs = SocialAccount.objects.filter(user=user)
        return qs.filter(provider='google').exists() or qs.filter(provider__istartswith='gocspx-').exists()

    from_google_flow = request.GET.get('from_google') == '1'

    google_clinic_completion = (
        request.user.is_authenticated
        and (_has_google_social(request.user) or from_google_flow)
        and not Clinic.objects.filter(user=request.user).exists()
    )

    if google_clinic_completion and request.user.user_type != 'clinic':
        request.user.user_type = 'clinic'
        request.user.save(update_fields=['user_type'])

    if request.method == 'POST':
        if google_clinic_completion:
            form = ClinicSignUpForm(request.POST, request.FILES, existing_user=request.user)
        else:
            form = ClinicSignUpForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                user = form.save()
                if not request.user.is_authenticated:
                    user.backend = 'django.contrib.auth.backends.ModelBackend'
                    login(request, user)
                messages.success(request, 'Clinic account created successfully! Your profile is now live.')
                return redirect('clinic_dashboard')
            except Exception as e:
                messages.error(request, f'An error occurred during registration: {str(e)}')
        else:
            for field_name, errors in form.errors.items():
                for error in errors:
                    if field_name == '__all__':
                        messages.error(request, f"Error: {error}")
                    else:
                        field_label = form.fields[field_name].label if field_name in form.fields else field_name
                        messages.error(request, f"{field_label}: {error}")
    else:
        if google_clinic_completion:
            initial = {
                'username': request.user.username,
                'email': request.user.email,
                'contact_email': request.user.email,
            }
            form = ClinicSignUpForm(existing_user=request.user, initial=initial)
            messages.info(request, 'Complete your clinic details to finish registration.')
        else:
            form = ClinicSignUpForm()

    # Add Google login context
    google_login_url = _get_google_login_url(request)
    context = {
        'form': form,
        'title': 'Clinic Registration',
        'google_prefill_mode': google_clinic_completion,
        'google_login_url': google_login_url,
    }
    context['google_clinic_start_url'] = reverse('google_start', kwargs={'role': 'clinic'})
    
    return render(request, 'clinics/signup.html', context)
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from decimal import Decimal, InvalidOperation
from django.contrib.auth import login
from django.core.files.storage import FileSystemStorage
import os
from accounts.forms import UserCreationForm
from patients.models import Patient, MedicalRecord
from .forms import AppointmentForm, ClinicSignUpForm, ClinicGalleryForm, ClinicServiceForm, ClinicUpdateForm
from .models import Appointment, Clinic, ClinicGallery, ClinicService
from posts.models import Post

def clinic_detail_view(request, clinic_id):
    logger.debug("Entered clinic_detail_view for clinic_id=%s, method=%s", clinic_id, request.method)
    clinic = get_object_or_404(Clinic, id=clinic_id)
    # Build context using helper to allow alternate views
    def _build_context(request, clinic):
        gallery_images = ClinicGallery.objects.filter(clinic=clinic)
        services = ClinicService.objects.filter(clinic=clinic)
        # Include posts that are either linked to this clinic or authored by the clinic user
        posts = Post.objects.filter(Q(clinic=clinic) | Q(author=clinic.user)).order_by('-created_at')
        # Only posts authored by this clinic's user
        clinic_posts = Post.objects.filter(author=clinic.user).order_by('-created_at')
        reviews = Review.objects.filter(clinic=clinic).select_related('patient').order_by('-created_at')
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        if avg_rating is not None:
            avg_rating = round(avg_rating, 1)
        else:
            avg_rating = None

        # Rating to display: if no reviews, default to 3.0
        reviews_count = reviews.count()
        if reviews_count == 0:
            display_rating = 3.0
        else:
            display_rating = avg_rating if avg_rating is not None else 3.0

        patient = None
        is_connected = False
        connection_status = None
        review_error = None
        if request.user.is_authenticated:
            try:
                patient = Patient.objects.get(user=request.user)
                if request.user.user_type == 'patient':
                    active_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='active').exists()
                    pending_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='pending').exists()
                    if active_connection:
                        is_connected = True
                        connection_status = 'active'
                    elif pending_connection:
                        is_connected = True
                        connection_status = 'pending'
            except Patient.DoesNotExist:
                logger.warning("[DEBUG] Patient.DoesNotExist for user %s", request.user)
                patient = None

        facilities_list = [f.strip() for f in clinic.facilities.split(',')] if clinic.facilities else []
        # Build acceptance fields list for the template: pairs (field_name, human_label)
        acceptance_fields = []
        try:
            for field in clinic._meta.fields:
                if field.name.startswith('accepts_'):
                    try:
                        accepted = getattr(clinic, field.name)
                    except Exception:
                        accepted = False
                    if accepted:
                        label = field.help_text if getattr(field, 'help_text', None) else str(field.verbose_name).replace('_', ' ').title()
                        acceptance_fields.append((field.name, label))
        except Exception:
            acceptance_fields = []
        context = {
            'clinic': clinic,
            'gallery_images': gallery_images,
            'services': services,
            'is_connected': is_connected,
            'connection_status': connection_status,
            'patient': patient,
            'facilities_list': facilities_list,
            'acceptance_fields': acceptance_fields,
            'posts': posts,
            'clinic_posts': clinic_posts,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'display_rating': display_rating,
            'reviews_count': reviews_count,
            'review_error': review_error,
            'clinic_detail_marker': 'CLINIC_DETAIL_VIEW_ACTIVE',
            'omit_booking': True,
        }
        return context

    context = _build_context(request, clinic)
    # Render the patient-facing clinic detail template (not the clinic-only view)
    return render(request, 'clinics/clinic_detail.html', context)


def clinic_detail_clinic_view(request, clinic_id):
    """Clinic-facing detail view without booking UI."""
    clinic = get_object_or_404(Clinic, id=clinic_id)
    def _build_context(request, clinic):
        gallery_images = ClinicGallery.objects.filter(clinic=clinic)
        services = ClinicService.objects.filter(clinic=clinic)
        # Include posts that are either linked to this clinic or authored by the clinic user
        posts = Post.objects.filter(Q(clinic=clinic) | Q(author=clinic.user)).order_by('-created_at')
        clinic_posts = Post.objects.filter(author=clinic.user).order_by('-created_at')
        reviews = Review.objects.filter(clinic=clinic).select_related('patient').order_by('-created_at')
        avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
        if avg_rating is not None:
            avg_rating = round(avg_rating, 1)
        else:
            avg_rating = None
        reviews_count = reviews.count()
        if reviews_count == 0:
            display_rating = 3.0
        else:
            display_rating = avg_rating if avg_rating is not None else 3.0
        patient = None
        is_connected = False
        connection_status = None
        review_error = None
        if request.user.is_authenticated:
            try:
                patient = Patient.objects.get(user=request.user)
                if request.user.user_type == 'patient':
                    active_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='active').exists()
                    pending_connection = Appointment.objects.filter(clinic=clinic, patient=patient, status='pending').exists()
                    if active_connection:
                        is_connected = True
                        connection_status = 'active'
                    elif pending_connection:
                        is_connected = True
                        connection_status = 'pending'
            except Patient.DoesNotExist:
                patient = None
        facilities_list = [f.strip() for f in clinic.facilities.split(',')] if clinic.facilities else []
        acceptance_fields = []
        try:
            for field in clinic._meta.fields:
                if field.name.startswith('accepts_'):
                    try:
                        accepted = getattr(clinic, field.name)
                    except Exception:
                        accepted = False
                    if accepted:
                        label = field.help_text if getattr(field, 'help_text', None) else str(field.verbose_name).replace('_', ' ').title()
                        acceptance_fields.append((field.name, label))
        except Exception:
            acceptance_fields = []
        context = {
            'clinic': clinic,
            'gallery_images': gallery_images,
            'services': services,
            'is_connected': is_connected,
            'connection_status': connection_status,
            'patient': patient,
            'facilities_list': facilities_list,
            'acceptance_fields': acceptance_fields,
            'posts': posts,
            'clinic_posts': clinic_posts,
            'reviews': reviews,
            'avg_rating': avg_rating,
            'display_rating': display_rating,
            'reviews_count': reviews_count,
            'review_error': review_error,
            'clinic_detail_marker': 'CLINIC_DETAIL_CLINIC_VIEW',
            'omit_booking': True,
        }
        return context

    context = _build_context(request, clinic)
    # Add current clinic (the logged-in clinic user) and unread count for header badges
    current_clinic = None
    total_unread = 0
    if request.user.is_authenticated and getattr(request.user, 'user_type', None) == 'clinic':
        try:
            current_clinic = Clinic.objects.get(user=request.user)
        except Clinic.DoesNotExist:
            current_clinic = None
        # compute unread messages for header badge
        try:
            from chat.models import ChatRoom, Message
            chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
            total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
        except Exception:
            total_unread = 0

    context.update({
        'current_clinic': current_clinic,
        'total_unread': total_unread,
    })

    return render(request, 'clinics/clinic_datils_clinic.html', context)
    

@login_required
def clinic_ping(request):
    """Simple endpoint for clinics to refresh their `last_seen` timestamp."""
    try:
        if hasattr(request.user, 'clinic'):
            from django.utils import timezone
            request.user.clinic.last_seen = timezone.now()
            request.user.clinic.save(update_fields=['last_seen'])
            return JsonResponse({'ok': True})
    except Exception:
        pass
    return JsonResponse({'ok': False}, status=400)


@login_required
def clinic_settings_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)

    if request.method == 'POST':
        form = ClinicUpdateForm(request.POST, request.FILES, instance=clinic)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clinic settings updated successfully!')
            return redirect('clinic_settings')
        messages.error(request, 'Could not save settings. Please fix the highlighted fields and try again.')
    else:
        form = ClinicUpdateForm(instance=clinic)

    context = {
        'clinic': clinic,
        'form': form,
    }
    return render(request, 'clinics/settings.html', context)



@login_required
def manage_gallery_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    
    if request.method == 'POST':
        form = ClinicGalleryForm(request.POST, request.FILES)
        if form.is_valid():
            gallery_item = form.save(commit=False)
            gallery_item.clinic = clinic
            gallery_item.save()
            messages.success(request, 'Image added to gallery!')
            return redirect('manage_gallery')
    else:
        form = ClinicGalleryForm()
    
    gallery_images = ClinicGallery.objects.filter(clinic=clinic)
    
    context = {
        'clinic': clinic,
        'form': form,
        'gallery_images': gallery_images,
    }
    return render(request, 'clinics/manage_gallery.html', context)

@login_required
def delete_gallery_image_view(request, image_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    image = get_object_or_404(ClinicGallery, id=image_id, clinic=clinic)
    
    if request.method == 'POST':
        image.delete()
        messages.success(request, 'Image deleted successfully!')
    
    return redirect('manage_gallery')


@login_required
@require_POST
def delete_clinic_service_view(request, service_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    service = get_object_or_404(ClinicService, id=service_id, clinic=clinic)

    # Best-effort cleanup of the uploaded file, if any.
    try:
        if getattr(service, 'photo', None):
            service.photo.delete(save=False)
    except Exception:
        pass

    service.delete()
    messages.success(request, 'Service deleted successfully!')
    return redirect('clinic_dashboard')


@login_required
def patient_detail_view(request, patient_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    patient = get_object_or_404(Patient, id=patient_id)

    assignment = get_object_or_404(Appointment, clinic=clinic, patient=patient)

    try:
        medical_record = MedicalRecord.objects.get(patient=patient)
    except MedicalRecord.DoesNotExist:
        medical_record = None
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=assignment, clinic=clinic, patient=assignment.patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Patient information updated successfully!')
            return redirect('patient_detail', patient_id=patient.id)
    else:
        form = AppointmentForm(instance=assignment, clinic=clinic, patient=assignment.patient)
    
    context = {
        'patient': patient,
        'medical_record': medical_record,
        'assignment': assignment,
        'form': form,
        'clinic': clinic,
    }
    return render(request, 'clinics/patient_detail.html', context)

@login_required
def search_patients_view(request):
    # Allow both clinics and patients to access this search. Clinics get clinic-specific behavior.
    if request.user.user_type not in ('clinic', 'patient'):
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = None
    if request.user.user_type == 'clinic':
        clinic = get_object_or_404(Clinic, user=request.user)

    query = request.GET.get('q', '') or ''
    query = query.strip()

    patients = []
    assigned_patients = None

    # If the current user is a clinic, provide their assigned patients for the empty state
    if clinic is not None:
        assigned_patients = Appointment.objects.filter(clinic=clinic).select_related('patient')

    if query:
        # support multi-token name searches (e.g., first + last)
        tokens = [t for t in query.split() if t]
        patients_qs = Patient.objects.all()

        # build OR queries for tokens across several fields
        q_obj = Q()
        for t in tokens:
            q_obj |= Q(full_name__icontains=t)
            q_obj |= Q(phone__icontains=t)
            q_obj |= Q(user__email__icontains=t)
            q_obj |= Q(user__username__icontains=t)

        patients_qs = patients_qs.filter(q_obj).order_by('full_name')

        # If a clinic is searching, exclude patients already linked to this clinic
        if clinic is not None:
            patients_qs = patients_qs.exclude(appointment__clinic=clinic)

        patients = patients_qs.distinct()[:50]

    context = {
        'patients': patients,
        'query': query,
        'clinic': clinic,
        'assigned_patients': assigned_patients,
    }
    return render(request, 'clinics/search_patients.html', context)


@login_required
def search_patient_clinic_page(request):
    """Render the full-page clinic patient search UI (simple wrapper around the AJAX partial).
    """
    if request.user.user_type not in ('clinic', 'patient'):
        return redirect('login')
    clinic = get_object_or_404(Clinic, user=request.user) if request.user.user_type == 'clinic' else None
    context = {'clinic': clinic}
    return render(request, 'clinics/search_patient_clinic.html', context)

@login_required
def assign_patient_view(request, patient_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    patient = get_object_or_404(Patient, id=patient_id)
    
    if Appointment.objects.filter(clinic=clinic, patient=patient).exists():
        messages.warning(request, 'This patient is already assigned to your clinic.')
        return redirect('clinic_dashboard')
    
    Appointment.objects.create(
        clinic=clinic,
        patient=patient,
        notes=f"Assigned on {request.user.date_joined.strftime('%Y-%m-%d')}"
    )
    
    messages.success(request, f'Patient {patient.full_name} has been assigned to your clinic!')
    return redirect('clinic_dashboard')



@login_required
def create_appointment_view(request, clinic_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, id=clinic_id)
    patient = get_object_or_404(Patient, user=request.user)
    
    medical_records = MedicalRecord.objects.filter(patient=patient)
    if not medical_records.exists():
        messages.error(request, 'You need to create a medical record before booking an appointment.')
        return redirect('medical_record_create')
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, patient=patient, clinic=clinic)
        if form.is_valid():
            appointment = form.save(commit=False)
            appointment.patient = patient
            appointment.clinic = clinic
            appointment.save()
            
            messages.success(request, 'Appointment request sent successfully! The clinic will review your booking.')
            return redirect('patient_appointments')
    else:
        form = AppointmentForm(patient=patient, clinic=clinic)
        # Set default date to tomorrow
        form.initial['appointment_date'] = date.today()
    
    context = {
        'form': form,
        'clinic': clinic,
        'patient': patient,
    }
    return render(request, 'clinics/create_appointment.html', context)

@login_required
def patient_appointments_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    patient = get_object_or_404(Patient, user=request.user)
    # Auto-clean stale appointments: remove appointments whose date passed by at least one day.
    cutoff_date = date.today() - timedelta(days=1)
    Appointment.objects.filter(appointment_date__lte=cutoff_date).delete()

    all_appointments = Appointment.objects.filter(patient=patient).select_related('clinic', 'medical_record')

    status_filter = (request.GET.get('status', '') or '').strip().lower()
    status_labels = dict(Appointment.STATUS_CHOICES)
    choice_order = [choice[0] for choice in Appointment.STATUS_CHOICES]
    allowed_statuses = set(choice_order)

    if status_filter and status_filter in allowed_statuses:
        appointments = all_appointments.filter(status__iexact=status_filter)
    else:
        appointments = all_appointments
        status_filter = ''

    status_filters = [
        {
            'value': value,
            'label': status_labels.get(value, value.replace('_', ' ').title()),
        }
        for value in choice_order
    ]

    total_appointments = all_appointments.count()
    # compute total_unread for header/sidebar badges
    from chat.models import ChatRoom, Message
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()

    context = {
        'appointments': appointments,
        'patient': patient,
        'status_filter': status_filter,
        'status_filters': status_filters,
        'total_appointments': total_appointments,
        'total_unread': total_unread,
    }
    return render(request, 'patient/appointments.html', context)

@login_required
def clinic_appointments_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    # Auto-clean stale terminal appointments only; never delete active lifecycle records.
    cutoff_date = date.today() - timedelta(days=1)
    Appointment.objects.filter(
        appointment_date__lte=cutoff_date,
        status__in=['cancelled', 'rejected_medical_record', 'completed'],
    ).delete()
    # Auto-clean completed lifecycle: remove upcoming records 2 days after treatment end date.
    upcoming_cleanup_date = date.today() - timedelta(days=2)
    Appointment.objects.filter(
        status='upcoming',
        treatment_end_date__isnull=False,
        treatment_end_date__lte=upcoming_cleanup_date,
    ).delete()

    appointments = Appointment.objects.filter(clinic=clinic).select_related('patient', 'medical_record')
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'upcoming':
        appointments = appointments.filter(status='upcoming')
    elif status_filter:
        appointments = appointments.filter(status=status_filter)
    
    total_appointments = Appointment.objects.filter(clinic=clinic).count()
    pending_appointments = Appointment.objects.filter(clinic=clinic, status='pending').count()
    accepted_appointments = Appointment.objects.filter(clinic=clinic, status__in=['accepted_record_accepted_accommodation', 'waiting_for_payment']).count()
    upcoming_appointments = Appointment.objects.filter(clinic=clinic, status='upcoming').count()
    
    context = {
        'appointments': appointments,
        'clinic': clinic,
        'status_filter': status_filter,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'accepted_appointments': accepted_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'clinics/clinic_appointments.html', context)

@login_required
def update_appointment_status_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Appointment.STATUS_CHOICES):
            appointment.status = new_status
            appointment.save()
            messages.success(request, f'Appointment status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid status.')
    
    return redirect('clinic_appointments')


@login_required
@require_POST
def accept_medical_record_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'pending':
        messages.error(request, 'Medical record already reviewed.')
        return redirect('clinic_appointments')

    appointment.medical_record_accepted = True
    appointment.medical_rejection_reason = ''
    appointment.save(update_fields=['medical_record_accepted', 'medical_rejection_reason', 'updated_at'])

    messages.success(request, 'Medical record accepted. Waiting for patient booking details.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def reject_medical_record_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'pending':
        messages.error(request, 'Medical record already reviewed.')
        return redirect('clinic_appointments')

    rejection_reason = (request.POST.get('medical_rejection_reason') or '').strip()
    if rejection_reason not in dict(Appointment.MEDICAL_REJECTION_REASON_CHOICES):
        messages.error(request, 'Please select a valid refusal reason.')
        return redirect('clinic_appointments')

    appointment.status = 'rejected_medical_record'
    appointment.medical_record_accepted = False
    appointment.medical_rejection_reason = rejection_reason
    appointment.save(update_fields=['status', 'medical_record_accepted', 'medical_rejection_reason', 'updated_at'])

    messages.success(request, 'Medical record rejected and appointment cancelled.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def facility_accept_requested_dates_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'pending':
        messages.error(request, 'Booking cannot be processed after review.')
        return redirect('clinic_appointments')

    if not appointment.treatment_start_date or not appointment.treatment_end_date:
        messages.error(request, 'Patient booking details are still missing.')
        return redirect('clinic_appointments')

    appointment.status = 'accepted_record_accepted_accommodation'
    appointment.proposed_start_date = None
    appointment.proposed_end_date = None
    appointment.clinic_proposal_note = ''
    appointment.appointment_date = appointment.treatment_start_date
    appointment.payment_due_at = None
    appointment.payment_amount = None
    appointment.save(
        update_fields=[
            'status',
            'proposed_start_date',
            'proposed_end_date',
            'clinic_proposal_note',
            'appointment_date',
            'payment_amount',
            'payment_due_at',
            'updated_at',
        ]
    )

    messages.success(request, 'Booking accepted. Please set the payment amount to request patient payment.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def set_payment_amount_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'accepted_record_accepted_accommodation':
        messages.error(request, 'You can only set payment amount after booking acceptance.')
        return redirect('clinic_appointments')

    payment_amount_raw = (request.POST.get('payment_amount') or '').strip()
    if not payment_amount_raw:
        messages.error(request, 'Please enter the amount to request from the patient.')
        return redirect('clinic_appointments')

    try:
        payment_amount = Decimal(payment_amount_raw)
    except InvalidOperation:
        messages.error(request, 'Please enter a valid payment amount.')
        return redirect('clinic_appointments')

    if payment_amount <= 0:
        messages.error(request, 'Payment amount must be greater than 0.')
        return redirect('clinic_appointments')

    appointment.payment_amount = payment_amount
    appointment.payment_due_at = timezone.now() + timedelta(hours=48)
    appointment.status = 'waiting_for_payment'
    appointment.save(update_fields=['payment_amount', 'payment_due_at', 'status', 'updated_at'])

    messages.success(request, 'Payment request sent to patient.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def mark_appointment_upcoming_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'paid':
        messages.error(request, 'Only paid appointments can be marked as upcoming.')
        return redirect('clinic_appointments')

    appointment.status = 'upcoming'
    appointment.save(update_fields=['status', 'updated_at'])

    messages.success(request, 'Appointment marked as upcoming.')
    return redirect('clinic_appointments')


@login_required
def clinic_google_calendar_start_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'upcoming':
        messages.error(request, 'Google Calendar is available only for upcoming appointments.')
        return redirect('clinic_appointments')

    if not _google_calendar_client_id() or not _google_calendar_client_secret():
        messages.error(request, 'Google Calendar credentials are missing. Please configure them in environment settings.')
        return redirect('clinic_appointments')

    if not (appointment.treatment_start_date or appointment.appointment_date):
        messages.error(request, 'This upcoming appointment has no dates yet, so it cannot be exported to Google Calendar.')
        return redirect('clinic_appointments')

    state = secrets.token_urlsafe(24)
    request.session['google_calendar_oauth_state'] = state
    request.session['google_calendar_pending_appointment_id'] = appointment.id
    request.session.modified = True

    params = {
        'client_id': _google_calendar_client_id(),
        'redirect_uri': _google_calendar_redirect_uri(request),
        'response_type': 'code',
        'scope': GOOGLE_CALENDAR_SCOPE,
        'access_type': 'offline',
        'include_granted_scopes': 'true',
        'prompt': 'consent',
        'state': state,
    }
    logger.warning(
        'Clinic Google Calendar OAuth start user_id=%s host=%s client_id=%s redirect_uri=%s',
        request.user.id,
        request.get_host(),
        params['client_id'],
        params['redirect_uri'],
    )
    return redirect(f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}")


@login_required
def clinic_google_calendar_callback_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    expected_state = request.session.get('google_calendar_oauth_state')
    returned_state = (request.GET.get('state') or '').strip()
    code = (request.GET.get('code') or '').strip()
    oauth_error = (request.GET.get('error') or '').strip()

    appointment_id = request.session.pop('google_calendar_pending_appointment_id', None)
    request.session.pop('google_calendar_oauth_state', None)

    if oauth_error:
        messages.error(request, 'Google Calendar could not be connected. Please try again.')
        return redirect('clinic_appointments')

    if not expected_state or not returned_state or expected_state != returned_state:
        messages.error(request, 'Google authorization state mismatch. Please try again.')
        return redirect('clinic_appointments')

    if not code or not appointment_id:
        messages.error(request, 'Missing Google authorization code or appointment context.')
        return redirect('clinic_appointments')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = Appointment.objects.filter(id=appointment_id, clinic=clinic).select_related('patient').first()
    if not appointment:
        messages.error(request, 'Appointment not found for Google Calendar sync.')
        return redirect('clinic_appointments')

    if appointment.status != 'upcoming':
        messages.error(request, 'Only upcoming appointments can be added to Google Calendar.')
        return redirect('clinic_appointments')

    payload = _build_google_calendar_event_payload(clinic, appointment)
    if not payload:
        messages.error(request, 'Appointment dates are missing, so no calendar event can be created.')
        return redirect('clinic_appointments')

    try:
        token_payload = _google_calendar_exchange_code(code, _google_calendar_redirect_uri(request))
        _save_google_calendar_token(request, token_payload)
    except HTTPError as exc:
        details = _google_http_error_message(exc)
        logger.warning('Google token exchange failed for clinic_id=%s status=%s details=%s', clinic.id, getattr(exc, 'code', 'unknown'), details)
        messages.error(request, f'Google token exchange failed: {details or "Unknown error"}')
        return redirect('clinic_appointments')
    except (URLError, TimeoutError, ValueError):
        messages.error(request, 'Network error while contacting Google Calendar.')
        return redirect('clinic_appointments')

    token_data = request.session.get('google_calendar_token', {})
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    if not access_token:
        messages.error(request, 'Google access token is missing. Please reconnect and try again.')
        return redirect('clinic_appointments')

    calendar_id = (getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary') or 'primary').strip() or 'primary'
    try:
        event = _google_calendar_create_event(access_token, payload, calendar_id=calendar_id)
    except HTTPError as exc:
        if getattr(exc, 'code', None) == 401 and refresh_token:
            try:
                refreshed = _google_calendar_refresh_token(refresh_token)
                _save_google_calendar_token(request, refreshed)
                token_data = request.session.get('google_calendar_token', {})
                event = _google_calendar_create_event(token_data.get('access_token'), payload, calendar_id=calendar_id)
            except Exception:
                messages.error(request, 'Google token expired and refresh failed. Please reconnect Google Calendar.')
                return redirect('clinic_appointments')
        else:
            details = _google_http_error_message(exc)
            logger.warning('Google Calendar event creation failed for clinic_id=%s status=%s details=%s', clinic.id, getattr(exc, 'code', 'unknown'), details)
            messages.error(request, 'We could not add this appointment to Google Calendar. Please try again.')
            return redirect('clinic_appointments')
    except (URLError, TimeoutError, ValueError):
        messages.error(request, 'Network error while creating Google Calendar event.')
        return redirect('clinic_appointments')

    event_link = (event or {}).get('htmlLink')
    if event_link:
        messages.success(request, 'Your appointment has been added to Google Calendar.')
    else:
        messages.success(request, 'Your appointment has been added to Google Calendar.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def facility_accept_propose_dates_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'pending':
        messages.error(request, 'Booking cannot be processed after review.')
        return redirect('clinic_appointments')

    if not appointment.treatment_start_date or not appointment.treatment_end_date:
        messages.error(request, 'Patient booking details are still missing.')
        return redirect('clinic_appointments')

    proposed_start_date = (request.POST.get('proposed_start_date') or '').strip()
    proposed_end_date = (request.POST.get('proposed_end_date') or '').strip()
    proposed_accommodation_type = (request.POST.get('proposed_accommodation_type') or '').strip()
    proposed_companions_raw = (request.POST.get('proposed_companions_count') or '').strip()
    clinic_proposal_note = (request.POST.get('clinic_proposal_note') or '').strip()

    has_date_change = bool(proposed_start_date or proposed_end_date)
    has_accommodation_change = bool(proposed_accommodation_type or proposed_companions_raw)
    if not has_date_change and not has_accommodation_change:
        messages.error(request, 'Please propose at least one change (dates or accommodation details).')
        return redirect('clinic_appointments')

    if has_date_change and (not proposed_start_date or not proposed_end_date):
        messages.error(request, 'Please provide both proposed start and end dates.')
        return redirect('clinic_appointments')

    if proposed_accommodation_type and proposed_accommodation_type not in dict(Appointment.ACCOMMODATION_TYPE_CHOICES):
        messages.error(request, 'Please select a valid accommodation type.')
        return redirect('clinic_appointments')

    if not clinic_proposal_note:
        messages.error(request, 'Please add a note explaining the proposed change.')
        return redirect('clinic_appointments')

    proposed_start = None
    proposed_end = None
    if has_date_change:
        try:
            proposed_start = datetime.strptime(proposed_start_date, '%Y-%m-%d').date()
            proposed_end = datetime.strptime(proposed_end_date, '%Y-%m-%d').date()
        except ValueError:
            messages.error(request, 'Invalid proposed date format.')
            return redirect('clinic_appointments')

        if proposed_end < proposed_start:
            messages.error(request, 'Proposed end date must be after the proposed start date.')
            return redirect('clinic_appointments')

        if proposed_start < date.today() or proposed_end < date.today():
            messages.error(request, 'Proposed dates must be today or later.')
            return redirect('clinic_appointments')

    room_type_map = {
        'single_room': 'single',
        'double_room': 'double',
        'double_suite': 'suite',
        'quad_suite': 'suite',
        'no_accommodation': '',
    }

    next_accommodation_type = proposed_accommodation_type or appointment.accommodation_type
    next_needs_accommodation = next_accommodation_type != 'no_accommodation'

    if proposed_companions_raw and (not proposed_companions_raw.isdigit() or int(proposed_companions_raw) < 0):
        messages.error(request, 'Please provide a valid companions count.')
        return redirect('clinic_appointments')

    if proposed_companions_raw:
        next_companions_count = int(proposed_companions_raw)
    elif next_needs_accommodation:
        next_companions_count = appointment.companions_count if appointment.companions_count is not None else 0
    else:
        next_companions_count = 0

    has_real_change = False
    if has_date_change and (
        appointment.treatment_start_date != proposed_start or appointment.treatment_end_date != proposed_end
    ):
        has_real_change = True
    if proposed_accommodation_type and appointment.accommodation_type != next_accommodation_type:
        has_real_change = True
    if proposed_companions_raw and (appointment.companions_count or 0) != next_companions_count:
        has_real_change = True

    if not has_real_change:
        messages.error(request, 'The proposal must change at least one value.')
        return redirect('clinic_appointments')

    appointment.status = 'accepted_record_accommodation_change_requested'
    appointment.proposed_start_date = proposed_start
    appointment.proposed_end_date = proposed_end
    appointment.accommodation_type = next_accommodation_type
    appointment.needs_accommodation = next_needs_accommodation
    appointment.companions_count = next_companions_count
    appointment.travelers_count = next_companions_count if next_needs_accommodation else None
    appointment.preferred_room_type = room_type_map.get(next_accommodation_type, '')
    appointment.clinic_proposal_note = clinic_proposal_note
    appointment.payment_due_at = None
    appointment.save(
        update_fields=[
            'status',
            'proposed_start_date',
            'proposed_end_date',
            'accommodation_type',
            'needs_accommodation',
            'companions_count',
            'travelers_count',
            'preferred_room_type',
            'clinic_proposal_note',
            'payment_due_at',
            'updated_at',
        ]
    )

    messages.success(request, 'Proposal sent to patient. Waiting for patient response.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def facility_reject_booking_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status not in ['pending', 'accepted_record_accommodation_change_requested']:
        messages.error(request, 'Booking cannot be rejected at this stage.')
        return redirect('clinic_appointments')

    appointment.status = 'cancelled'
    appointment.save(update_fields=['status', 'updated_at'])

    messages.success(request, 'Booking cancelled.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def accept_with_accommodation_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'pending' or not appointment.needs_accommodation:
        messages.error(request, 'Accommodation decision is not available for this request.')
        return redirect('clinic_appointments')

    appointment.status = 'accepted_record_accepted_accommodation'
    appointment.appointment_date = appointment.treatment_start_date
    appointment.payment_amount = None
    appointment.payment_due_at = None
    appointment.save(update_fields=['status', 'appointment_date', 'payment_amount', 'payment_due_at', 'updated_at'])

    messages.success(request, 'Request accepted with accommodation. Set payment amount to request payment.')
    return redirect('clinic_appointments')


@login_required
@require_POST
def accept_without_accommodation_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)

    if appointment.status != 'pending' or not appointment.needs_accommodation:
        messages.error(request, 'Accommodation decision is not available for this request.')
        return redirect('clinic_appointments')

    appointment.status = 'accepted_record_accepted_accommodation'
    appointment.appointment_date = appointment.treatment_start_date
    appointment.payment_amount = None
    appointment.payment_due_at = None
    appointment.save(update_fields=['status', 'appointment_date', 'payment_amount', 'payment_due_at', 'updated_at'])

    messages.success(request, 'Request accepted without accommodation. Set payment amount to request payment.')
    return redirect('clinic_appointments')


@login_required
def update_appointment_view(request, appointment_id):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    clinic = get_object_or_404(Clinic, user=request.user)
    appointment = get_object_or_404(Appointment, id=appointment_id, clinic=clinic)
    
    if request.method == 'POST':
        form = AppointmentForm(request.POST, instance=appointment, clinic=clinic, patient=appointment.patient)
        if form.is_valid():
            form.save()
            messages.success(request, 'Appointment updated successfully!')
            return redirect('clinic_appointments')
    else:
        form = AppointmentForm(instance=appointment, clinic=clinic, patient=appointment.patient)
    
    context = {
        'form': form,
        'appointment': appointment,
        'clinic': clinic,
    }
    return render(request, 'clinics/edit_appointment.html', context)


@login_required
def clinic_my_posts_view(request):
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    # posts authored by this clinic user
    my_posts = Post.objects.filter(clinic=clinic, author=request.user).order_by('-created_at')

    context = {
        'clinic': clinic,
        'my_posts': my_posts,
    }
    return render(request, 'clinics/clinic_my_posts.html', context)


@login_required
@require_POST
def delete_post_view(request, post_id):
    from posts.models import Post
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    post = get_object_or_404(Post, id=post_id, clinic=clinic)

    # Only allow deletion if the requesting user is the author
    if post.author != request.user:
        messages.error(request, 'You do not have permission to delete this post.')
        return redirect('clinic_my_posts')

    post.delete()
    messages.success(request, 'Post deleted successfully.')
    return redirect('clinic_my_posts')


@login_required
@require_POST
def edit_post_view(request, post_id):
    from posts.models import Post
    if request.user.user_type != 'clinic':
        messages.error(request, 'Access denied.')
        return redirect('login')

    clinic = get_object_or_404(Clinic, user=request.user)
    post = get_object_or_404(Post, id=post_id, clinic=clinic)

    if post.author != request.user:
        messages.error(request, 'You do not have permission to edit this post.')
        return redirect('clinic_my_posts')

    description = (request.POST.get('description') or '').strip()
    if not description:
        messages.error(request, 'Post description cannot be empty.')
        return redirect('clinic_my_posts')

    post.description = description
    post.save(update_fields=['description'])
    messages.success(request, 'Post updated successfully.')
    return redirect('clinic_my_posts')
