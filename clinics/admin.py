from django.contrib import admin
from .models import Clinic, ClinicGallery, ClinicService, Appointment

@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
    list_display = (
        "clinic_name",
        "user",
        "city",
        "state",
        "specialization",
        "age_range",
        "accepts_heart_problems",
        "accepts_permanent_catheter",
        "accepts_intermittent_catheter",
        "accepts_wheelchair",
        "accepts_walker",
        "accepts_crutch",
        "accepts_bowel_incontinence",
        "accepts_urine_incontinence",
        "accepts_medical_condom",
        "accepts_diapers",
        "accepts_breathing_issues",
        "accepts_feeding_tube",
        "accepts_stool_tube",
        "accepts_urine_tube",
        "accepts_bedsores",
        "accepts_diabetes",
        "accepts_insulin",
        "accepts_high_blood_pressure",
        "accepts_infectious_diseases",
        "accepts_vein_thrombosis",
        "accepts_depression",
        "accepts_tracheostomy_tube",
        "accepts_dependent_patients",
        "accepts_bedridden_patients",
        "is_verified",
    )
    search_fields = (
        "clinic_name",
        "city",
        "state",
        "user__username",
        "contact_email",
    )
    list_filter = (
        "specialization",
        "is_verified",
        "age_range",
        "accepts_heart_problems",
        "accepts_permanent_catheter",
        "accepts_intermittent_catheter",
        "accepts_wheelchair",
        "accepts_walker",
        "accepts_crutch",
        "accepts_bowel_incontinence",
        "accepts_urine_incontinence",
        "accepts_medical_condom",
        "accepts_diapers",
        "accepts_breathing_issues",
        "accepts_feeding_tube",
        "accepts_stool_tube",
        "accepts_urine_tube",
        "accepts_bedsores",
        "accepts_diabetes",
        "accepts_insulin",
        "accepts_high_blood_pressure",
        "accepts_infectious_diseases",
        "accepts_vein_thrombosis",
        "accepts_depression",
        "accepts_tracheostomy_tube",
        "accepts_dependent_patients",
        "accepts_bedridden_patients",
    )


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
