from django.contrib import admin
from .models import Patient, MedicalRecord

@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):
	list_display = ("full_name", "user", "date_of_birth", "gender", "phone")
	search_fields = ("full_name", "phone", "user__email", "user__username")
	list_filter = ("gender",)

@admin.register(MedicalRecord)
class MedicalRecordAdmin(admin.ModelAdmin):
	list_display = (
		"patient", "first_name", "last_name", "main_diagnosis",
		"movement_ability", "has_heart_problems", "created_at"
	)
	search_fields = ("first_name", "last_name", "main_diagnosis", "patient__full_name")
	list_filter = ("movement_ability", "has_heart_problems")