from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.http import HttpResponseForbidden, HttpResponse, Http404, FileResponse, JsonResponse
from django.conf import settings
from django.urls import reverse
from clinics.models import Appointment
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from django.shortcuts import get_object_or_404
import mimetypes
import os
import io
import logging
import json
import secrets
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from cryptography.fernet import InvalidToken

logger = logging.getLogger(__name__)

NERO_AI_WEBHOOK_URL = os.environ.get(
    'NERO_AI_WEBHOOK_URL',
    'https://hook.we.make.com/ymrxo8uemoy8dlmdvrm4wa4ttd69771k',
)


GOOGLE_OAUTH_AUTH_URL = 'https://accounts.google.com/o/oauth2/v2/auth'
GOOGLE_OAUTH_TOKEN_URL = 'https://oauth2.googleapis.com/token'
GOOGLE_CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar.events'


def _google_calendar_client_id():
    return (getattr(settings, 'GOOGLE_CALENDAR_CLIENT_ID', '') or '').strip()


def _google_calendar_client_secret():
    return (getattr(settings, 'GOOGLE_CALENDAR_CLIENT_SECRET', '') or '').strip()


def _patient_google_calendar_redirect_uri(request):
    base = (getattr(settings, 'GOOGLE_CALENDAR_REDIRECT_BASE', '') or '').strip().rstrip('/')
    path = reverse('patient_google_calendar_callback')
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
    existing = request.session.get('patient_google_calendar_token', {})
    access_token = token_payload.get('access_token') or existing.get('access_token')
    refresh_token = token_payload.get('refresh_token') or existing.get('refresh_token')
    expires_in = int(token_payload.get('expires_in') or existing.get('expires_in') or 3600)
    request.session['patient_google_calendar_token'] = {
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


def _build_patient_google_calendar_event_payload(appointment):
    start_date = appointment.treatment_start_date or appointment.appointment_date
    end_date = appointment.treatment_end_date or start_date
    if not start_date:
        return None
    if end_date and end_date < start_date:
        end_date = start_date

    clinic = appointment.clinic
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
        'summary': f'Upcoming appointment - {clinic.clinic_name}',
        'location': location,
        'description': '\n'.join(details),
        'start': {'date': start_date.isoformat()},
        'end': {'date': (end_date + timedelta(days=1)).isoformat()},
    }


@require_POST
@csrf_protect
def nero_ai_chat_api(request):
    """King George chat webhook. Open to anonymous visitors (e.g. the public
    landing page) as well as logged-in patients (the dashboard widget)."""
    try:
        payload = json.loads(request.body.decode('utf-8') or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'reply': 'Invalid request payload.'}, status=400)

    message = (payload.get('message') or '').strip()
    if not message:
        return JsonResponse({'reply': 'Please type a message first.'}, status=400)

    if request.user.is_authenticated:
        patient_name = getattr(request.user, 'username', 'patient')
        if hasattr(request.user, 'patient') and getattr(request.user.patient, 'full_name', ''):
            patient_name = request.user.patient.full_name
        patient_id = request.user.id
        patient_username = request.user.username
        source = 'nero_patient_dashboard'
    else:
        patient_name = 'Guest visitor'
        patient_id = None
        patient_username = ''
        source = 'nero_landing_page'

    clinics_context = list(
        Clinic.objects.values('clinic_name', 'description').order_by('clinic_name')
    )

    from django.utils.translation import get_language
    webhook_payload = {
        'message': message,
        'patient_id': patient_id,
        'patient_username': patient_username,
        'patient_name': patient_name,
        'clinics': clinics_context,
        'source': source,
        'language': get_language() or 'en',  # Make scenario: reply in this language
        'sent_at': timezone.now().isoformat(),
    }

    try:
        req = Request(
            NERO_AI_WEBHOOK_URL,
            data=json.dumps(webhook_payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                # Make.com / Cloudflare block the default "Python-urllib" UA (403);
                # send a normal UA + Accept so the webhook is reachable.
                'User-Agent': 'Nero/1.0 (+https://nero-69la.onrender.com)',
                'Accept': 'application/json, text/plain, */*',
            },
            method='POST',
        )
        with urlopen(req, timeout=25) as resp:
            raw = resp.read().decode('utf-8', errors='replace').strip()
            content_type = (resp.headers.get('Content-Type') or '').lower()
    except (HTTPError, URLError, TimeoutError) as exc:
        logger.exception('NERO AI webhook call failed: %s', exc)
        return JsonResponse(
            {
                'reply': (
                    'I received your message, but the assistant is temporarily unavailable. '
                    'Please try again in a moment. You can also use Smart Recommendations for a faster clinic match.'
                )
            },
            status=200,
        )

    reply_text = ''
    if raw:
        if 'application/json' in content_type or raw.startswith('{'):
            try:
                response_json = json.loads(raw)
                reply_text = (
                    response_json.get('reply')
                    or response_json.get('response')
                    or response_json.get('message')
                    or response_json.get('text')
                    or ''
                )
            except json.JSONDecodeError:
                reply_text = raw
        else:
            reply_text = raw

    if not reply_text:
        reply_text = (
            'Your message was sent successfully. I recommend using Smart Recommendations '
            'to quickly find the best clinic match for your case.'
        )

    return JsonResponse({'reply': reply_text})

# Delete appointment view
@login_required
@require_POST
def delete_appointment_view(request, appointment_id):
    appointment = get_object_or_404(Appointment, id=appointment_id)
    # Only allow the patient who owns the appointment to delete
    if appointment.patient.user != request.user:
        return HttpResponseForbidden("You do not have permission to delete this appointment.")
    if appointment.status not in ['completed', 'cancelled', 'rejected', 'rejected_medical_record']:
        messages.error(request, 'Only completed, cancelled, or rejected appointments can be deleted.')
        return redirect('patient_appointments')
    appointment.delete()
    messages.success(request, "Appointment deleted successfully.")
    return redirect('patient_appointments')
from accounts.forms import PatientSignUpForm
from .forms import PatientForm, MedicalRecordForm
from .models import Patient, MedicalRecord, MedicalRecordReport, MedicalRecordVideo
from django.db.models import Q, Avg
from clinics.models import Appointment, Clinic, ClinicService
from django.core.paginator import Paginator
import random
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from accounts.social_signals import sync_google_patient_avatar_for_user


def _clinic_has_record_appointment(user, medical_record):
    """Return True only when this clinic user has an appointment for this exact record."""
    if getattr(user, 'user_type', None) != 'clinic':
        return False
    return Appointment.objects.filter(
        clinic__user=user,
        medical_record=medical_record,
        patient=medical_record.patient,
    ).exists()


def _can_access_medical_record(user, medical_record):
    """Owner patient, assigned clinic (via appointment), or staff can access."""
    if not getattr(user, 'is_authenticated', False):
        return False
    if user.is_staff:
        return True
    if user == medical_record.patient.user:
        return True
    return _clinic_has_record_appointment(user, medical_record)

def patient_signup_view(request):
    if request.method == 'POST':
        user_form = PatientSignUpForm(request.POST, request.FILES)
        if user_form.is_valid():
            user = user_form.save()
            user.backend = 'django.contrib.auth.backends.ModelBackend'
            login(request, user)
            messages.success(request, 'Account created successfully! Your dashboard is ready.')
            return redirect('patient_dashboard')
    else:
        user_form = PatientSignUpForm()

    # Add Google login context
    from accounts.views import _get_google_login_url
    from django.urls import reverse
    google_login_url = _get_google_login_url(request)
    context = {
        'form': user_form,
        'google_login_url': google_login_url,
    }
    if google_login_url:
        context['google_patient_start_url'] = reverse('google_start', kwargs={'role': 'patient'})
    else:
        context['google_patient_start_url'] = None

    return render(request, 'patient/signup.html', context)


def _save_additional_medical_files(request, medical_record):
    report_files = request.FILES.getlist('medical_report_files')
    video_files = request.FILES.getlist('movement_video_files')

    for report in report_files:
        if report:
            obj = MedicalRecordReport(medical_record=medical_record, file=report)
            obj.full_clean()
            obj.save()

    for video in video_files:
        if video:
            obj = MedicalRecordVideo(medical_record=medical_record, file=video)
            obj.full_clean()
            obj.save()

@login_required
def medical_record_create_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    patient, _ = Patient.objects.get_or_create(user=request.user)
    initial_contact_data = {
        'email': request.user.email or '',
        'mobile_number': patient.phone or '',
        'whatsapp_number': patient.phone or '',
    }
    if request.method == 'POST':
        medical_form = MedicalRecordForm(request.POST, request.FILES)

        if medical_form.is_valid():
            from django.core.exceptions import ValidationError
            from django.utils.http import url_has_allowed_host_and_scheme
            try:
                # All-or-nothing: the record and its attached report/video files
                # must commit together, or not at all (no orphaned partial writes).
                with transaction.atomic():
                    medical_record = medical_form.save(commit=False)
                    medical_record.patient = patient
                    medical_record.save()
                    _save_additional_medical_files(request, medical_record)
            except ValidationError as exc:
                logger.warning('Medical record file validation failed for user %s: %s', request.user.pk, exc)
                messages.error(
                    request,
                    'Could not save one or more attached files. Please check the file '
                    'type and size and try again.',
                )
            else:
                messages.success(request, 'Medical record created successfully!')

                # Only honour `next` if it is a safe, same-site URL — a plain
                # substring check would let an attacker pass https://evil.com/questionnaire.
                next_url = request.POST.get('next') or request.GET.get('next')
                is_safe_next = bool(
                    next_url
                    and 'questionnaire' in next_url
                    and url_has_allowed_host_and_scheme(
                        next_url,
                        allowed_hosts={request.get_host()},
                        require_https=request.is_secure(),
                    )
                )
                if is_safe_next:
                    sep = '&' if '?' in next_url else '?'
                    return redirect(f"{next_url}{sep}new_record_id={medical_record.id}")
                return redirect(f"{reverse('recommendations:questionnaire')}?new_record_id={medical_record.id}")
        else:
            logger.debug('Medical record form invalid: %s', medical_form.errors)
    else:
        medical_form = MedicalRecordForm(initial=initial_contact_data)

    # Ensure patient form is always available to the template (so `patient` and its avatar can render)
    patient_form = PatientForm(instance=patient)
    context = {
        'patient_form': patient_form,
        'medical_form': medical_form,
        'patient': patient,
        'medical_record': None,
        'medical_record_reports': [],
        'medical_record_videos': [],
        'next': request.GET.get('next', ''),
    }
    return render(request, 'patient/medical_record_form.html', context)

@login_required
def medical_record_success_view(request):
    try:
        patient = Patient.objects.get(user=request.user)
        has_records = MedicalRecord.objects.filter(patient=patient).exists()
    except Patient.DoesNotExist:
        has_records = False
    # Provide patient and latest medical record so template can show avatar and summary
    medical_record = None
    is_update = request.GET.get('update', '0') == '1'
    try:
        if has_records:
            medical_record = MedicalRecord.objects.filter(patient=patient).order_by('-updated_at').first()
    except Exception:
        medical_record = None

    context = {
        'has_records': has_records,
        'patient': patient if 'patient' in locals() else None,
        'medical_record': medical_record,
        'is_update': is_update,
    }
    return render(request, 'patient/medical_record_success.html', context)

@login_required
def patient_dashboard_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    from clinics.models import Clinic
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None

    # Recover missing avatar for Google patient accounts when social signals were missed.
    if patient and not bool(getattr(patient.profile_picture, 'name', '')):
        if sync_google_patient_avatar_for_user(request.user):
            patient.refresh_from_db(fields=['profile_picture'])

    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')

    upcoming_appointments = 0
    pending_appointments = 0
    recent_appointments = None
    suggested_clinics = []
    active_patients = []

    if medical_records.exists():
        from datetime import date
        appointments = Appointment.objects.filter(patient=patient)
        upcoming_appointments = appointments.filter(
            status='accepted',
            appointment_date__gte=date.today()
        ).count()
        pending_appointments = appointments.filter(status='pending').count()
        recent_appointments = appointments.select_related('clinic').order_by('-created_at')[:3]

        # Get the most recent medical record
        last_record = medical_records.first()
        # Try to match by address (city or region info). Prioritize clinics
        # whose `city` or `address` contains the patient's city (exact match first),
        # then fill remaining slots with other clinics (randomized).
        # Build scored recommendations based on multiple signals from the medical record
        # Weights (tunable): reviews 40%, city/address 30%, service 15%, acceptance 15%
        REVIEW_W = 0.40
        CITY_W = 0.30
        SERVICE_W = 0.15
        ACCEPT_W = 0.15

        # Extract city token from medical record address
        addr = (last_record.address or '').strip()
        city_candidate = addr.split(',')[0].strip().lower() if addr else ''

        # Patient's requested service (optional)
        desired_service = (last_record.main_diagnosis or '').strip().lower()

        from reviews.models import Review

        clinics_qs = Clinic.objects.all()
        scored = []
        for clinic in clinics_qs:
            # Review score: average rating normalized to [0,1]
            try:
                rv = Review.objects.filter(clinic=clinic).aggregate(avg=Avg('rating'))['avg']
            except Exception:
                rv = None
            review_score = (rv / 5.0) if rv else 0.0

            # City/address match score
            city_score = 0.0
            if city_candidate:
                if clinic.city and city_candidate == clinic.city.strip().lower():
                    city_score = 1.0
                elif city_candidate in (clinic.address or '').lower():
                    city_score = 0.6
                elif city_candidate in (clinic.city or '').lower():
                    city_score = 0.8

            # Service match score (check clinic services and specialization)
            service_score = 0.0
            if desired_service:
                try:
                    svc_match = clinic.services.filter(service_name__icontains=desired_service).exists()
                except Exception:
                    svc_match = False
                if svc_match:
                    service_score = 1.0
                elif desired_service in (clinic.specialization or '').lower():
                    service_score = 0.7

            # Acceptance score: ensure clinic accepts the patient's special conditions
            # Map medical record boolean fields to clinic acceptance fields
            condition_map = [
                ('uses_wheelchair', 'accepts_wheelchair'),
                ('uses_walker', 'accepts_walker'),
                ('uses_crutch', 'accepts_crutch'),
                ('uses_electric_wheelchair', 'accepts_electric_wheelchair'),
                ('has_bedsores', 'accepts_bedsores'),
                ('has_diabetes', 'accepts_diabetes'),
                ('uses_insulin', 'accepts_insulin'),
                ('has_heart_problems', 'accepts_heart_problems'),
                ('has_high_blood_pressure', 'accepts_high_blood_pressure'),
                ('has_infectious_diseases', 'accepts_infectious_diseases'),
                ('has_vein_thrombosis', 'accepts_vein_thrombosis'),
                ('has_depression', 'accepts_depression'),
                ('uses_permanent_catheter', 'accepts_catheter'),
                ('uses_intermittent_catheter', 'accepts_catheter'),
                ('uses_medical_condom', 'accepts_medical_condom'),
                ('uses_diapers', 'accepts_diapers'),
            ]
            required_conditions = 0
            accepts_ok = 0
            for mr_field, clinic_field in condition_map:
                try:
                    if getattr(last_record, mr_field, False):
                        required_conditions += 1
                        if getattr(clinic, clinic_field, False):
                            accepts_ok += 1
                except Exception:
                    continue

            if required_conditions == 0:
                acceptance_score = 1.0
            else:
                acceptance_score = accepts_ok / required_conditions

            # Final weighted score
            final_score = (REVIEW_W * review_score) + (CITY_W * city_score) + (SERVICE_W * service_score) + (ACCEPT_W * acceptance_score)

            scored.append((final_score, review_score, clinic))

        # Sort by final score desc, then by review_score desc
        scored.sort(key=lambda x: (x[0], x[1]), reverse=True)
        suggested_clinics = [c for _, _, c in scored][:3]

    # --- Active Community Members: 3 random online patients we've chatted with ---
    from chat.models import ChatRoom, Message
    from accounts.models import User
    # Find all chat rooms involving this user
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    # compute total unread across all chat rooms for this user
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()
    # Find all unique patient users we've chatted with (excluding self)
    patient_user_ids = set()
    for room in chat_rooms:
        other = room.user2 if room.user1 == request.user else room.user1
        # Only include if other is a patient
        try:
            patient_obj = Patient.objects.get(user=other)
            patient_user_ids.add(patient_obj.id)
        except Patient.DoesNotExist:
            continue
    # Simulate online status: patients with a message in the last 5 minutes
    from django.utils import timezone
    from datetime import timedelta
    now = timezone.now()
    online_patients = []
    for pid in patient_user_ids:
        user = Patient.objects.get(id=pid).user
        recent_msg = Message.objects.filter(sender=user, timestamp__gte=now-timedelta(minutes=5)).exists()
        if recent_msg:
            online_patients.append(Patient.objects.get(id=pid))
    random.shuffle(online_patients)
    active_patients = online_patients[:3]

    # Calculate is_online for active_patients based on last_seen (5-min threshold)
    for member in active_patients:
        try:
            is_online = False
            if member.last_seen:
                is_online = (now - member.last_seen) <= timedelta(minutes=5)
            member.is_online = is_online
        except Exception:
            member.is_online = False

    # Fallback: last 3 people we've chatted with, ordered by most recent message
    last_chatted_patients = []
    if not active_patients:
        # Get all messages sent or received by the user, order by timestamp desc
        chat_messages = Message.objects.filter(
            chat_room__in=chat_rooms
        ).exclude(sender=request.user).order_by('-timestamp')
        seen_patient_ids = set()
        for msg in chat_messages:
            try:
                patient_obj = Patient.objects.get(user=msg.sender)
                if patient_obj.id not in seen_patient_ids:
                    last_chatted_patients.append(patient_obj)
                    seen_patient_ids.add(patient_obj.id)
                if len(last_chatted_patients) >= 3:
                    break
            except Patient.DoesNotExist:
                continue

    # Calculate is_online for last_chatted_patients based on last_seen (5-min threshold)
    for member in last_chatted_patients:
        try:
            is_online = False
            if member.last_seen:
                is_online = (now - member.last_seen) <= timedelta(minutes=5)
            member.is_online = is_online
        except Exception:
            member.is_online = False

    # --- Post Creation ---
    from posts.models import Post
    from clinics.models import Clinic
    post_error = None
    if request.method == 'POST' and 'post_content' in request.POST:
        description = request.POST.get('post_content', '').strip()
        image = request.FILES.get('post_image')
        video = request.FILES.get('post_video')
        # For patient, let them pick a clinic or assign to first clinic (or null)
        clinic = Clinic.objects.first() if Clinic.objects.exists() else None
        if description and clinic:
            Post.objects.create(
                clinic=clinic,
                author=request.user,
                description=description,
                image=image if image else None,
                video=video if video else None
            )
            messages.success(request, 'Post created successfully!')
            return redirect('patient_dashboard')
        else:
            post_error = 'Please write something to post.'

    posts = Post.objects.all().order_by('-created_at')
    my_posts = posts.filter(author=request.user)

    return render(request, 'patient/dashboard/patient_dashboard.html', {
        'patient': patient,
        'show_onboarding': bool(patient and not patient.onboarding_done),
        'medical_records': medical_records,
        'upcoming_appointments': upcoming_appointments,
        'pending_appointments': pending_appointments,
        'recent_appointments': recent_appointments,
        'suggested_clinics': suggested_clinics,
        'active_patients': active_patients,
        'last_chatted_patients': last_chatted_patients,
        'posts': posts,
        'my_posts': my_posts,
        'post_error': post_error,
        'total_unread': total_unread,
    })


@login_required
def patient_my_posts_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')
    from posts.models import Post
    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None
    my_posts = Post.objects.filter(author=request.user).order_by('-created_at')
    # compute total_unread for header/sidebar badges
    from chat.models import ChatRoom, Message
    chat_rooms = ChatRoom.objects.filter(Q(user1=request.user) | Q(user2=request.user))
    total_unread = Message.objects.filter(chat_room__in=chat_rooms, is_read=False).exclude(sender=request.user).count()

    return render(request, 'patient/dashboard/my_posts.html', {
        'patient': patient,
        'my_posts': my_posts,
        'total_unread': total_unread,
    })


@login_required
@require_POST
def delete_my_post_view(request, post_id):
    from posts.models import Post
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return HttpResponseForbidden("You do not have permission to delete this post.")
    post.delete()
    messages.success(request, 'Post deleted successfully.')
    return redirect('patient_my_posts')


@login_required
@require_POST
def edit_my_post_view(request, post_id):
    from posts.models import Post
    post = get_object_or_404(Post, id=post_id)
    if post.author != request.user:
        return HttpResponseForbidden("You do not have permission to edit this post.")

    description = (request.POST.get('description') or '').strip()
    if not description:
        messages.error(request, 'Post description cannot be empty.')
        return redirect('patient_my_posts')

    post.description = description
    post.save(update_fields=['description'])
    messages.success(request, 'Post updated successfully.')
    return redirect('patient_my_posts')

@login_required
def patient_medical_records_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None

    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-created_at')

    context = {
        'patient': patient,
        'medical_records': medical_records,
    }
    return render(request, 'patient/medical_records.html', context)

@login_required
def see_medical_record_view(request, record_id=None):



    if record_id:
        medical_record = get_object_or_404(MedicalRecord, id=record_id)

        if not _can_access_medical_record(request.user, medical_record):
            return HttpResponseForbidden('You do not have permission to access this medical record.')

        appointment = None
        if hasattr(request.user, 'user_type') and request.user.user_type == 'clinic':
            appointment = (
                Appointment.objects.filter(
                    medical_record=medical_record,
                    clinic__user=request.user,
                )
                .select_related('clinic', 'patient')
                .order_by('-created_at')
                .first()
            )
        context = {
            'medical_record': medical_record,
            'appointment': appointment,
            'single_record': True
        }
        if hasattr(request.user, 'user_type') and request.user.user_type == 'clinic':
            return render(request, 'clinics/see_medical_record_clinic.html', context)
        else:
            return render(request, 'patient/see_medical_record.html', context)
    else:
        context = {
            'single_record': False
        }
        if hasattr(request.user, 'user_type') and request.user.user_type == 'clinic':
            return render(request, 'clinics/see_medical_record_clinic.html', context)
        else:
            return render(request, 'patient/see_medical_record.html', context)


@login_required
def secure_medical_report_download(request, record_id):
    """Return decrypted medical report using storage.open()."""
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    if not _can_access_medical_record(request.user, medical_record):
        return HttpResponseForbidden('You do not have permission to access this file.')

    if not medical_record.medical_reports:
        raise Http404('No medical report attached to this record.')

    # Open via storage to get decrypted bytes and stream via FileResponse
    try:
        f = medical_record.medical_reports.open('rb')
        data = f.read()
    except InvalidToken:
        logger.exception('Failed to decrypt medical report for record %s', record_id)
        return HttpResponse('Failed to decrypt file. Check server encryption settings.', status=500)
    except Exception:
        logger.exception('Error reading medical report for record %s', record_id)
        return HttpResponse('Failed to read file from storage.', status=500)
    finally:
        try:
            f.close()
        except Exception:
            pass

    filename = os.path.basename(medical_record.medical_reports.name)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'application/octet-stream'

    buffer = io.BytesIO(data)
    response = FileResponse(buffer, content_type=content_type)
    response['Content-Length'] = str(len(data))
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
def secure_movement_video_view(request, record_id):
    """Return decrypted movement video (inline) using storage.open()."""
    medical_record = get_object_or_404(MedicalRecord, id=record_id)

    if not _can_access_medical_record(request.user, medical_record):
        return HttpResponseForbidden('You do not have permission to access this file.')

    if not medical_record.patient_movement_video:
        raise Http404('No movement video attached to this record.')

    try:
        f = medical_record.patient_movement_video.open('rb')
        data = f.read()
    except InvalidToken:
        logger.exception('Failed to decrypt movement video for record %s', record_id)
        return HttpResponse('Failed to decrypt video. Check server encryption settings.', status=500)
    except Exception:
        logger.exception('Error reading movement video for record %s', record_id)
        return HttpResponse('Failed to read video from storage.', status=500)
    finally:
        try:
            f.close()
        except Exception:
            pass

    filename = os.path.basename(medical_record.patient_movement_video.name)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'video/mp4'

    buffer = io.BytesIO(data)
    response = FileResponse(buffer, content_type=content_type)
    response['Content-Length'] = str(len(data))
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response


@login_required
def secure_encrypted_media(request, blob_name):
    """Generic decrypt-and-stream proxy for EncryptedFileSystemStorage files.

    URL:  /patients/secure-media/<blob_name>/
    e.g.  /patients/secure-media/medical_reports/abc.pdf
          /patients/secure-media/movement_videos/x.mp4

    Permission rules:
    - The patient who owns the MedicalRecord that contains the file.
    - The specific clinic user who has an appointment for that record.
    - Staff users.
    """
    from .storage import EncryptedFileSystemStorage
    from .models import MedicalRecord, MedicalRecordReport, MedicalRecordVideo

    # Find owning MedicalRecord
    record = (
        MedicalRecord.objects.filter(medical_reports=blob_name).first()
        or MedicalRecord.objects.filter(patient_movement_video=blob_name).first()
        or MedicalRecord.objects.filter(reports__file=blob_name).first()
        or MedicalRecord.objects.filter(videos__file=blob_name).first()
    )
    if record is None:
        raise Http404('File not found.')

    # Authorization
    if not _can_access_medical_record(request.user, record):
        return HttpResponseForbidden('You do not have permission to access this file.')

    # Decrypt and stream
    storage = EncryptedFileSystemStorage()
    try:
        f = storage.open(blob_name, 'rb')
        data = f.read()
    except InvalidToken:
        logger.exception('Failed to decrypt encrypted media: %s', blob_name)
        return HttpResponse('Decryption failed.', status=500)
    except Exception:
        logger.exception('Error reading encrypted media: %s', blob_name)
        return HttpResponse('Failed to read file.', status=500)

    filename = os.path.basename(blob_name)
    content_type, _ = mimetypes.guess_type(filename)
    if not content_type:
        content_type = 'application/octet-stream'

    # Inline for images/video, attachment for PDFs/unknown
    disposition = 'inline' if content_type.startswith(('image/', 'video/')) else 'attachment'

    response = FileResponse(io.BytesIO(data), content_type=content_type)
    response['Content-Length'] = str(len(data))
    response['Content-Disposition'] = f'{disposition}; filename="{filename}"'
    return response

def search_clinics_view(request):
    query = request.GET.get('q', '')
    specialization = request.GET.get('specialization', 'all')
    city = request.GET.get('city', '')
    all_clinics = Clinic.objects.all()
    featured_clinics = None
    clinics_to_display = None
    if not query and specialization == 'all' and not city:
        clinic_list = list(all_clinics)
        if clinic_list:
            featured_clinics = random.sample(clinic_list, min(6, len(clinic_list)))
    else:
        clinics = all_clinics
        if query:
            clinics = clinics.filter(
                Q(clinic_name__icontains=query) |
                Q(description__icontains=query) |
                Q(tagline__icontains=query) |
                Q(specialization__icontains=query) |
                Q(city__icontains=query) |
                Q(state__icontains=query)
            )
        if specialization and specialization != 'all':
            clinics = clinics.filter(specialization__icontains=specialization)

        if city:
            clinics = clinics.filter(city__icontains=city)

        paginator = Paginator(clinics, 9)
        page_number = request.GET.get('page', 1)
        clinics_to_display = paginator.get_page(page_number)

    # Add patient to context for profile display
    patient = Patient.objects.get(user=request.user)
    context = {
        'clinics': clinics_to_display,
        'featured_clinics': featured_clinics,
        'query': query,
        'specialization': specialization,
        'city': city,
        'specialization_choices': Clinic.SPECIALIZATION_CHOICES,
        'patient': patient,
    }

    return render(request, 'patient/search_clinics.html', context)

@login_required
def medical_record_update_view(request, pk):
    record = get_object_or_404(MedicalRecord, pk=pk, patient=request.user.patient)
    if request.method == 'POST':
        form = MedicalRecordForm(request.POST, request.FILES, instance=record)
        if form.is_valid():
            form.save()
            _save_additional_medical_files(request, record)
            messages.success(request, 'Medical record updated successfully!')
            return redirect(f"{redirect('recommendations:questionnaire').url}?medical_record_id={record.id}")
    else:
        form = MedicalRecordForm(instance=record)

    # Include patient and record in context so template can render profile info
    return render(request, 'patient/medical_record_form.html', {
        'medical_form': form,
        'patient': record.patient,
        'medical_record': record,
        'medical_record_reports': record.reports.all().order_by('-created_at'),
        'medical_record_videos': record.videos.all().order_by('-created_at'),
    })

@login_required
def medical_record_delete_view(request, pk):
    """Delete a medical record belonging to the current patient.

    Note: This view performs deletion immediately to align with the existing
    anchor link in the dashboard template. Consider changing the template to
    submit a POST request for safer semantics.
    """
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    record = get_object_or_404(MedicalRecord, pk=pk, patient=request.user.patient)
    record.delete()
    messages.success(request, 'Medical record deleted successfully.')
    return redirect('patient_dashboard')

@login_required
def patient_appointments_view(request):
    if request.user.user_type != 'patient':
        logger.warning(f'Appointments access denied for user {request.user.id} ({request.user.username}) with user_type={request.user.user_type}')
        messages.error(request, f'Access denied. Your account type is: {request.user.user_type or "not set"}. Expected: patient')
        return redirect('login')

    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        logger.error(f'Patient profile missing for user {request.user.id} ({request.user.username})')
        messages.error(request, 'Error: Your patient profile is missing. Please contact support.')
        return redirect('login')
    except Exception as e:
        logger.exception(f'Error fetching patient for user {request.user.id}: {e}')
        messages.error(request, f'Error: {str(e)}')
        return redirect('login')

    try:
        patient = Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        patient = None

    # Auto-clean stale terminal appointments only; keep active lifecycle records.
    from datetime import date, timedelta
    cutoff_date = date.today() - timedelta(days=1)
    Appointment.objects.filter(
        appointment_date__lte=cutoff_date,
        status__in=['cancelled', 'rejected', 'completed'],
    ).delete()
    # Auto-clean completed lifecycle: remove upcoming records 2 days after treatment end date.
    upcoming_cleanup_date = date.today() - timedelta(days=2)
    Appointment.objects.filter(
        status='upcoming',
        treatment_end_date__isnull=False,
        treatment_end_date__lte=upcoming_cleanup_date,
    ).delete()

    all_appointments = Appointment.objects.filter(patient=patient).select_related('clinic', 'medical_record').order_by('-appointment_date', '-created_at')

    status_filter = request.GET.get('status', '') or ''
    status_filter = status_filter.strip()

    # Build filters from real model statuses so all valid options are always visible.
    status_labels = dict(Appointment.STATUS_CHOICES)
    choice_order = [choice[0] for choice in Appointment.STATUS_CHOICES]
    status_filters = [
        {
            'value': value,
            'label': status_labels.get(value, value.replace('_', ' ').title()),
        }
        for value in choice_order
    ]

    status_filter_normalized = status_filter.lower()
    allowed_statuses = set(choice_order)

    if status_filter_normalized and status_filter_normalized in allowed_statuses:
        appointments = all_appointments.filter(status__iexact=status_filter_normalized)
        status_filter = status_filter_normalized
    else:
        appointments = all_appointments
        status_filter = ''

    total_appointments = all_appointments.count()
    pending_appointments = all_appointments.filter(status='pending').count()
    accepted_appointments = all_appointments.filter(status__in=['accepted_record_accepted_accommodation', 'waiting_for_payment']).count()
    upcoming_appointments = all_appointments.filter(status__in=['paid', 'upcoming']).count()

    context = {
        'patient': patient,
        'appointments': appointments,
        'status_filter': status_filter,
        'status_filters': status_filters,
        'total_appointments': total_appointments,
        'pending_appointments': pending_appointments,
        'accepted_appointments': accepted_appointments,
        'upcoming_appointments': upcoming_appointments,
    }
    return render(request, 'patient/appointments.html', context)

@login_required
def cancel_appointment_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient)

    # Only allow cancel before payment is due
    if appointment.status in ['payed', 'completed', 'cancelled', 'rejected']:
        messages.error(request, 'You cannot cancel this appointment at this stage.')
        return redirect('patient_appointments')

    if request.method == 'POST':
        appointment.status = 'cancelled'
        appointment.save()
        messages.success(request, 'Appointment cancelled successfully.')

    return redirect('patient_appointments')


@login_required
@require_POST
def submit_booking_details_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient)
    if appointment.status not in ['pending', 'accepted_record_accommodation_change_requested']:
        messages.error(request, 'Booking details can only be submitted for pending or clinic-proposed appointments.')
        return redirect('patient_appointments')
    if appointment.status not in ['pending', 'accepted_record_accommodation_change_requested']:
        messages.error(request, 'Accommodation details can only be submitted while the request is pending or awaiting accommodation.')
        return redirect('patient_appointments')

    accommodation_type = (request.POST.get('accommodation_type') or '').strip()
    companions_raw = (request.POST.get('companions_count') or '').strip()
    treatment_start_raw = (request.POST.get('treatment_start_date') or '').strip()
    treatment_end_raw = (request.POST.get('treatment_end_date') or '').strip()

    if accommodation_type not in dict(Appointment.ACCOMMODATION_TYPE_CHOICES):
        messages.error(request, 'Please select a valid accommodation type.')
        return redirect('patient_appointments')

    room_type_map = {
        'single_room': 'single',
        'double_room': 'double',
        'double_suite': 'suite',
        'quad_suite': 'suite',
        'no_accommodation': '',
    }
    needs_accommodation = accommodation_type != 'no_accommodation'

    if not needs_accommodation:
        appointment.companions_count = 0
        appointment.accommodation_type = 'no_accommodation'
        appointment.needs_accommodation = False
        appointment.travelers_count = None
        appointment.preferred_room_type = ''
        appointment.treatment_start_date = None
        appointment.treatment_end_date = None
        appointment.proposed_start_date = None
        appointment.proposed_end_date = None
        appointment.status = 'accepted_record_accepted_accommodation'
        appointment.appointment_date = None
        appointment.payment_amount = None
        appointment.payment_due_at = None
        appointment.save(
            update_fields=[
                'companions_count',
                'accommodation_type',
                'needs_accommodation',
                'travelers_count',
                'preferred_room_type',
                'treatment_start_date',
                'treatment_end_date',
                'proposed_start_date',
                'proposed_end_date',
                'status',
                'appointment_date',
                'payment_amount',
                'payment_due_at',
                'updated_at',
            ]
        )

        messages.success(request, 'Booking confirmed. Waiting for clinic to set payment amount.')
        return redirect('patient_appointments')

    if not companions_raw or not companions_raw.isdigit() or int(companions_raw) < 0:
        messages.error(request, 'Please provide a valid number of companions.')
        return redirect('patient_appointments')

    if not treatment_start_raw or not treatment_end_raw:
        messages.error(request, 'Please provide treatment start and end dates.')
        return redirect('patient_appointments')

    try:
        treatment_start = datetime.strptime(treatment_start_raw, '%Y-%m-%d').date()
        treatment_end = datetime.strptime(treatment_end_raw, '%Y-%m-%d').date()
    except ValueError:
        messages.error(request, 'Invalid treatment date format.')
        return redirect('patient_appointments')

    if treatment_end < treatment_start:
        messages.error(request, 'Treatment end date must be after the start date.')
        return redirect('patient_appointments')

    appointment.companions_count = int(companions_raw)
    appointment.accommodation_type = accommodation_type
    appointment.needs_accommodation = needs_accommodation
    appointment.travelers_count = int(companions_raw) if needs_accommodation else None
    appointment.preferred_room_type = room_type_map.get(accommodation_type, '')
    appointment.treatment_start_date = treatment_start
    appointment.treatment_end_date = treatment_end
    appointment.status = 'pending'
    appointment.payment_due_at = None
    appointment.save(
        update_fields=[
            'companions_count',
            'accommodation_type',
            'needs_accommodation',
            'travelers_count',
            'preferred_room_type',
            'treatment_start_date',
            'treatment_end_date',
            'status',
            'payment_due_at',
            'updated_at',
        ]
    )

    messages.success(request, 'Booking details submitted. Waiting for clinic review.')
    return redirect('patient_appointments')


@login_required
@require_POST
def patient_accept_proposed_dates_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient)
    if appointment.status != 'accepted_record_accommodation_change_requested':
        messages.error(request, 'There are no proposed changes to accept.')
        return redirect('patient_appointments')

    patient_response_note = (request.POST.get('patient_response_note') or '').strip()

    # Clinic proposals may include dates, accommodation details, or both.
    # Apply proposed dates only when provided.
    if appointment.proposed_start_date and appointment.proposed_end_date:
        appointment.treatment_start_date = appointment.proposed_start_date
        appointment.treatment_end_date = appointment.proposed_end_date
        appointment.appointment_date = appointment.proposed_start_date

    appointment.patient_response_note = patient_response_note
    appointment.status = 'accepted_record_accepted_accommodation'
    appointment.payment_amount = None
    appointment.payment_due_at = None
    appointment.save(
        update_fields=[
            'treatment_start_date',
            'treatment_end_date',
            'appointment_date',
            'patient_response_note',
            'status',
            'payment_amount',
            'payment_due_at',
            'updated_at',
        ]
    )

    messages.success(request, 'Proposal accepted. Waiting for clinic to set payment amount.')
    return redirect('patient_appointments')


@login_required
@require_POST
def patient_choose_different_dates_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient)
    if appointment.status != 'accepted_record_accommodation_change_requested':
        messages.error(request, 'You can only request different dates after a clinic proposal.')
        return redirect('patient_appointments')

    patient_response_note = (request.POST.get('patient_response_note') or '').strip()

    appointment.patient_response_note = patient_response_note
    appointment.status = 'pending'
    appointment.payment_due_at = None
    appointment.save(
        update_fields=[
            'patient_response_note',
            'status',
            'payment_due_at',
            'updated_at',
        ]
    )

    messages.success(request, 'Your requested changes were sent to the clinic. Waiting for clinic response.')
    return redirect('patient_appointments')


@login_required
@require_POST
def patient_confirm_payment_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    patient = request.user.patient

    with transaction.atomic():
        appointment = get_object_or_404(
            Appointment.objects.select_for_update(),
            id=appointment_id,
            patient=patient,
        )

        if appointment.status != 'waiting_for_payment':
            messages.error(request, 'Payment can only be confirmed when the booking is waiting for payment.')
            return redirect('patient_appointments')

        if not appointment.payment_amount or appointment.payment_amount <= 0:
            messages.error(request, 'Clinic has not set a payment amount yet.')
            return redirect('patient_appointments')

        appointment.status = 'paid'
        appointment.paid_at = timezone.now()
        appointment.payment_due_at = None
        appointment.save(update_fields=['status', 'paid_at', 'payment_due_at', 'updated_at'])

        competing_statuses = [
            'pending',
            'accepted_record_accepted_accommodation',
            'accepted_record_accommodation_change_requested',
            'waiting_for_payment',
        ]
        cancelled_count = (
            Appointment.objects.filter(
                patient=patient,
                medical_record=appointment.medical_record,
                status__in=competing_statuses,
            )
            .exclude(id=appointment.id)
            .update(status='cancelled', updated_at=timezone.now())
        )

    if cancelled_count:
        messages.success(request, f'Payment confirmed. Your appointment is now confirmed and {cancelled_count} other pending offer(s) were cancelled.')
    else:
        messages.success(request, 'Payment confirmed. Your appointment is now confirmed.')

    return redirect('patient_appointments')


@login_required
def patient_google_calendar_start_view(request, appointment_id):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    appointment = get_object_or_404(Appointment, id=appointment_id, patient=request.user.patient)
    if appointment.status != 'upcoming':
        messages.error(request, 'Google Calendar is available only for upcoming appointments.')
        return redirect('patient_appointments')

    if not _google_calendar_client_id() or not _google_calendar_client_secret():
        messages.error(request, 'Google Calendar credentials are missing. Please configure them in environment settings.')
        return redirect('patient_appointments')

    if not (appointment.treatment_start_date or appointment.appointment_date):
        messages.error(request, 'This upcoming appointment has no dates yet, so it cannot be exported to Google Calendar.')
        return redirect('patient_appointments')

    state = secrets.token_urlsafe(24)
    request.session['patient_google_calendar_oauth_state'] = state
    request.session['patient_google_calendar_pending_appointment_id'] = appointment.id
    request.session.modified = True

    params = {
        'client_id': _google_calendar_client_id(),
        'redirect_uri': _patient_google_calendar_redirect_uri(request),
        'response_type': 'code',
        'scope': GOOGLE_CALENDAR_SCOPE,
        'access_type': 'offline',
        'include_granted_scopes': 'true',
        'prompt': 'consent',
        'state': state,
    }
    logger.warning(
        'Patient Google Calendar OAuth start user_id=%s host=%s client_id=%s redirect_uri=%s',
        request.user.id,
        request.get_host(),
        params['client_id'],
        params['redirect_uri'],
    )
    return redirect(f"{GOOGLE_OAUTH_AUTH_URL}?{urlencode(params)}")


@login_required
def patient_google_calendar_callback_view(request):
    if request.user.user_type != 'patient':
        messages.error(request, 'Access denied.')
        return redirect('login')

    expected_state = request.session.get('patient_google_calendar_oauth_state')
    returned_state = (request.GET.get('state') or '').strip()
    code = (request.GET.get('code') or '').strip()
    oauth_error = (request.GET.get('error') or '').strip()

    appointment_id = request.session.pop('patient_google_calendar_pending_appointment_id', None)
    request.session.pop('patient_google_calendar_oauth_state', None)

    if oauth_error:
        messages.error(request, 'Google Calendar could not be connected. Please try again.')
        return redirect('patient_appointments')

    if not expected_state or not returned_state or expected_state != returned_state:
        messages.error(request, 'Google authorization state mismatch. Please try again.')
        return redirect('patient_appointments')

    if not code or not appointment_id:
        messages.error(request, 'Missing Google authorization code or appointment context.')
        return redirect('patient_appointments')

    appointment = Appointment.objects.filter(
        id=appointment_id,
        patient=request.user.patient,
    ).select_related('patient', 'clinic').first()
    if not appointment:
        messages.error(request, 'Appointment not found for Google Calendar sync.')
        return redirect('patient_appointments')

    if appointment.status != 'upcoming':
        messages.error(request, 'Only upcoming appointments can be added to Google Calendar.')
        return redirect('patient_appointments')

    payload = _build_patient_google_calendar_event_payload(appointment)
    if not payload:
        messages.error(request, 'Appointment dates are missing, so no calendar event can be created.')
        return redirect('patient_appointments')

    try:
        token_payload = _google_calendar_exchange_code(code, _patient_google_calendar_redirect_uri(request))
        _save_google_calendar_token(request, token_payload)
    except HTTPError as exc:
        details = _google_http_error_message(exc)
        logger.warning('Google token exchange failed for patient_id=%s status=%s details=%s', request.user.id, getattr(exc, 'code', 'unknown'), details)
        messages.error(request, f'Google token exchange failed: {details or "Unknown error"}')
        return redirect('patient_appointments')
    except (URLError, TimeoutError, ValueError):
        messages.error(request, 'Network error while contacting Google Calendar.')
        return redirect('patient_appointments')

    token_data = request.session.get('patient_google_calendar_token', {})
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    if not access_token:
        messages.error(request, 'Google access token is missing. Please reconnect and try again.')
        return redirect('patient_appointments')

    calendar_id = (getattr(settings, 'GOOGLE_CALENDAR_ID', 'primary') or 'primary').strip() or 'primary'
    try:
        event = _google_calendar_create_event(access_token, payload, calendar_id=calendar_id)
    except HTTPError as exc:
        if getattr(exc, 'code', None) == 401 and refresh_token:
            try:
                refreshed = _google_calendar_refresh_token(refresh_token)
                _save_google_calendar_token(request, refreshed)
                token_data = request.session.get('patient_google_calendar_token', {})
                event = _google_calendar_create_event(token_data.get('access_token'), payload, calendar_id=calendar_id)
            except Exception:
                messages.error(request, 'Google token expired and refresh failed. Please reconnect Google Calendar.')
                return redirect('patient_appointments')
        else:
            details = _google_http_error_message(exc)
            logger.warning('Google Calendar event creation failed for patient_id=%s status=%s details=%s', request.user.id, getattr(exc, 'code', 'unknown'), details)
            messages.error(request, 'We could not add this appointment to Google Calendar. Please try again.')
            return redirect('patient_appointments')
    except (URLError, TimeoutError, ValueError):
        messages.error(request, 'Network error while creating Google Calendar event.')
        return redirect('patient_appointments')

    event_link = (event or {}).get('htmlLink')
    if event_link:
        messages.success(request, 'Your appointment has been added to Google Calendar.')
    else:
        messages.success(request, 'Your appointment has been added to Google Calendar.')
    return redirect('patient_appointments')
