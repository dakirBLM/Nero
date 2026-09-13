from django.contrib import admin
from .models import Clinic, ClinicGallery, ClinicService, Appointment, ClinicType, Specialization, Facility

@admin.register(ClinicType)
class ClinicTypeAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)

@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)

@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
	list_display = ("name",)
	search_fields = ("name",)

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
	list_display = (
		"clinic_name", "user", "city", "state",
		"accepts_heart_problems", "accepts_permanent_catheter",
		"accepts_intermittent_catheter", "is_verified"
	)
	search_fields = ("clinic_name", "city", "state", "user__username", "contact_email")
	list_filter = ("is_verified", "age_range", "accepts_heart_problems", "accepts_permanent_catheter", "accepts_intermittent_catheter", "clinic_types", "specializations")
	filter_horizontal = ("clinic_types", "specializations", "facilities")
	exclude = (
		"number_of_therapists",
		"hours_of_operation",
		"last_seen",
		"facebook_url",
		"instagram_url",
		"linkedin_url",
		"accepts_electric_wheelchair",
		# Legacy columns — synced automatically from the structured fields.
		"accepts_catheter",
		"clinic_type",
		"specialization",
		"facilities_text",
		"established_date",
	)

	def save_model(self, request, obj, form, change):
		super().save_model(request, obj, form, change)
		form.save_m2m()
		obj.sync_legacy_fields()

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
