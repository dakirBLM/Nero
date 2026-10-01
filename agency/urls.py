from django.urls import path

from clinics import views as clinic_views

from . import views

# Appointment actions reuse the clinic views; ``clinic_id`` in the path switches
# them into agency mode. Names are ``agency_<clinic url name>`` so templates can
# resolve either variant with the ``action_url`` tag.
_APPOINTMENT_ACTIONS = (
    ('update-status', clinic_views.update_appointment_status_view, 'update_appointment_status'),
    ('medical-accept', clinic_views.accept_medical_record_view, 'accept_medical_record'),
    ('medical-reject', clinic_views.reject_medical_record_view, 'reject_medical_record'),
    ('facility-accept-requested-dates', clinic_views.facility_accept_requested_dates_view, 'facility_accept_requested_dates'),
    ('set-payment-amount', clinic_views.set_payment_amount_view, 'set_payment_amount'),
    ('mark-upcoming', clinic_views.mark_appointment_upcoming_view, 'mark_appointment_upcoming'),
    ('facility-propose-dates', clinic_views.facility_accept_propose_dates_view, 'facility_propose_dates'),
    ('facility-reject-booking', clinic_views.facility_reject_booking_view, 'facility_reject_booking'),
    ('accommodation-with', clinic_views.accept_with_accommodation_view, 'accept_with_accommodation'),
    ('accommodation-without', clinic_views.accept_without_accommodation_view, 'accept_without_accommodation'),
    ('send-patient-details', views.send_patient_details_view, 'send_patient_details'),
)

urlpatterns = [
    path('login/', views.agency_login_view, name='agency_login'),
    path('logout/', views.agency_logout_view, name='agency_logout'),
    path('', views.agency_dashboard_view, name='agency_dashboard'),
    path('clinics/<int:clinic_id>/appointments/', clinic_views.clinic_appointments_view, name='agency_clinic_appointments'),
] + [
    path(f'clinics/<int:clinic_id>/appointment/<int:appointment_id>/{slug}/', view, name=f'agency_{name}')
    for slug, view, name in _APPOINTMENT_ACTIONS
]
