from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from clinics.models import Appointment, Clinic

from .auth import agency_required, check_agency_password, is_agency_authenticated, lock_agency, unlock_agency
from .emails import send_patient_details_email

ACCEPTED_STATUSES = ('accepted_record_accepted_accommodation', 'waiting_for_payment')
RECENT_APPOINTMENTS_LIMIT = 50


def _safe_next_url(request):
    candidate = request.POST.get('next') or request.GET.get('next') or ''
    if candidate and url_has_allowed_host_and_scheme(candidate, allowed_hosts={request.get_host()}):
        return candidate
    return reverse('agency_dashboard')


def agency_login_view(request):
    if is_agency_authenticated(request):
        return redirect('agency_dashboard')

    error = ''
    if request.method == 'POST':
        if check_agency_password(request.POST.get('password', '')):
            unlock_agency(request)
            return redirect(_safe_next_url(request))
        error = 'Incorrect password.'

    return render(request, 'agency/login.html', {'error': error, 'next': request.GET.get('next', '')})


@require_POST
def agency_logout_view(request):
    lock_agency(request)
    return redirect('agency_login')


@agency_required
def agency_dashboard_view(request):
    status_filter = request.GET.get('status', '')
    valid_statuses = dict(Appointment.STATUS_CHOICES)
    if status_filter not in valid_statuses:
        status_filter = ''

    clinics = Clinic.objects.annotate(
        total_count=Count('appointment'),
        pending_count=Count('appointment', filter=Q(appointment__status='pending')),
        accepted_count=Count('appointment', filter=Q(appointment__status__in=ACCEPTED_STATUSES)),
        upcoming_count=Count('appointment', filter=Q(appointment__status='upcoming')),
    ).order_by('clinic_name')

    appointments = Appointment.objects.select_related('clinic', 'patient', 'medical_record').order_by('-updated_at')
    if status_filter:
        appointments = appointments.filter(status=status_filter)

    counts_by_status = {
        row['status']: row['count']
        for row in Appointment.objects.values('status').annotate(count=Count('id'))
    }
    status_summary = [
        (value, label, counts_by_status.get(value, 0))
        for value, label in Appointment.STATUS_CHOICES
    ]

    context = {
        'clinics': clinics,
        'appointments': appointments[:RECENT_APPOINTMENTS_LIMIT],
        'status_filter': status_filter,
        'status_summary': status_summary,
        'total_appointments': sum(counts_by_status.values()),
    }
    return render(request, 'agency/dashboard.html', context)


@agency_required
@require_POST
def send_patient_details_view(request, clinic_id, appointment_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)
    appointment = get_object_or_404(
        Appointment.objects.select_related('patient__user', 'medical_record', 'clinic'),
        id=appointment_id,
        clinic=clinic,
    )
    back = redirect('agency_clinic_appointments', clinic_id=clinic.id)

    to_email = (request.POST.get('email') or '').strip()
    try:
        validate_email(to_email)
    except ValidationError:
        messages.error(request, 'Please enter a valid email address.')
        return back

    result = send_patient_details_email(appointment, to_email, request.build_absolute_uri('/').rstrip('/'))
    if not result.sent:
        messages.error(request, f'The email to {to_email} could not be sent. Check the email settings and try again.')
        return back

    summary = f'Patient details for {appointment.patient.full_name} sent to {to_email}'
    summary += f' with {len(result.attached)} attachment(s).' if result.attached else '.'
    if result.skipped:
        summary += ' Not attached: ' + ', '.join(f'{name} ({reason})' for _label, name, reason in result.skipped)
    messages.success(request, summary)
    return back
