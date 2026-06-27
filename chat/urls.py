from django.urls import path
from . import views_patient, views_clinic, views

urlpatterns = [
    path('rooms/', views_patient.chat_room_list_patient, name='chat_room_list'),
    path('room/<int:room_id>/', views_patient.chat_room_view_patient, name='chat_room_view'),
    path('room/<int:room_id>/send/', views.send_message, name='send_message'),
    path('start/', views.start_chat_with_clinic, name='start_chat_with_clinic'),
    path('start_user/', views.start_chat_with_user, name='start_chat_with_user'),
    path('start_patient_clinic/', views_clinic.start_chat_with_patient_clinic, name='start_chat_with_patient_clinic'),
    path('start_clinic_as_clinic/<int:clinic_id>/', views_clinic.start_chat_with_clinic_as_clinic, name='start_chat_with_clinic_as_clinic'),
    path('room/<int:room_id>/mark_read/', views.mark_messages_as_read, name='mark_messages_as_read'),
    path('rooms/patient/', views_patient.chat_room_list_patient, name='chat_room_list_patient'),
    path('room/patient/<int:room_id>/', views_patient.chat_room_view_patient, name='chat_room_view_patient'),
    path('rooms/clinic/', views_clinic.chat_room_list_clinic, name='chat_room_list_clinic'),
    path('room/clinic/<int:room_id>/', views_clinic.chat_room_view_clinic, name='chat_room_view_clinic'),
    path('unread-count/clinic/', views_clinic.unread_count_clinic, name='chat_unread_count_clinic'),
]
