from django.contrib import admin
from .models import Clinic, ClinicGallery, ClinicService, Appointment

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
	list_display = (
		"clinic_name", "user", "city", "state", "specialization",
		"accepts_heart_problems", "accepts_catheter", "is_verified"
	)
	search_fields = ("clinic_name", "city", "state", "user__username", "contact_email")
	list_filter = ("specialization", "is_verified", "accepts_heart_problems", "accepts_catheter")

@admin.register(ClinicService)
class ClinicServiceAdmin(admin.ModelAdmin):
	list_display = ("clinic", "service_name", "price_range")
	search_fields = ("service_name", "clinic__clinic_name")

@admin.register(ClinicGallery)
class ClinicGalleryAdmin(admin.ModelAdmin):
	list_display = ("clinic", "caption", "uploaded_at")
	search_fields = ("caption", "clinic__clinic_name")

@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
	list_display = (
		"patient", "clinic", "medical_record", "appointment_date",
		"appointment_time", "status", "created_at"
	)
	search_fields = (
		"patient__full_name", "clinic__clinic_name", "medical_record__main_diagnosis"
	)
	list_filter = ("status", "appointment_date", "clinic")
