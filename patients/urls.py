from django.urls import path

from . import views
from .views_settings import patient_settings_view, connect_google_account_view
from .search_all import search_all_view, search_patients_for_clinic_view

urlpatterns = [
    path('signup/', views.patient_signup_view, name='patient_signup'),
    path('dashboard/', views.patient_dashboard_view, name='patient_dashboard'),
    path('medical-records/', views.patient_medical_records_view, name='patient_medical_records'),
    path('medical-record/create/', views.medical_record_create_view, name='medical_record_create'),
    path('medical-record/success/', views.medical_record_success_view, name='medical_record_success'),
    path('search-clinics/', views.search_clinics_view, name='search_clinics'),
    path('medical-record/<int:pk>/update/', views.medical_record_update_view, name='medical_record_update'),
    path('medical-record/<int:pk>/delete/', views.medical_record_delete_view, name='medical_record_delete'),
    path('medical-record/<int:record_id>/download-report/', views.secure_medical_report_download, name='secure_medical_report_download'),
    path('medical-record/<int:record_id>/view-video/', views.secure_movement_video_view, name='secure_movement_video_view'),
    # Generic decrypt-and-stream proxy for encrypted media fields
    path('secure-media/<path:blob_name>/', views.secure_encrypted_media, name='secure_encrypted_media'),
    path('appointments/', views.patient_appointments_view, name='patient_appointments'),
    path('appointment/<int:appointment_id>/cancel/', views.cancel_appointment_view, name='cancel_appointment'),
    path('appointment/<int:appointment_id>/submit-booking-details/', views.submit_booking_details_view, name='submit_booking_details'),
    path('appointment/<int:appointment_id>/confirm-payment/', views.patient_confirm_payment_view, name='patient_confirm_payment'),
    path('appointment/<int:appointment_id>/google-calendar/start/', views.patient_google_calendar_start_view, name='patient_google_calendar_start'),
    path('google-calendar/callback/', views.patient_google_calendar_callback_view, name='patient_google_calendar_callback'),
    path('appointment/<int:appointment_id>/accept-proposed-dates/', views.patient_accept_proposed_dates_view, name='patient_accept_proposed_dates'),
    path('appointment/<int:appointment_id>/choose-different-dates/', views.patient_choose_different_dates_view, name='patient_choose_different_dates'),
    path('see-medical-record<int:record_id>/' , views.see_medical_record_view , name ='see_medical_record_view'),
    path('appointment/<int:appointment_id>/delete/', views.delete_appointment_view, name='delete_appointment')

    ,path('my-posts/', views.patient_my_posts_view, name='patient_my_posts')
    ,path('my-posts/<int:post_id>/edit/', views.edit_my_post_view, name='patient_edit_post')
    ,path('my-posts/<int:post_id>/delete/', views.delete_my_post_view, name='patient_delete_post')

    # Combined search for patients and clinics
    ,path('search-all/', search_all_view, name='search_all')
    # Clinic-facing patient search (AJAX partial)
    ,path('search-for-clinic/', search_patients_for_clinic_view, name='search_patients_for_clinic')

    # Patient settings
    ,path('settings/', patient_settings_view, name='patient_settings')
    ,path('settings/connect-google/', connect_google_account_view, name='patient_connect_google')

]