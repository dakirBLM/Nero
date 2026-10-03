from django import forms
from django.contrib import admin

from .models import Clinic, ClinicGallery, ClinicService, Appointment


class ClinicAdminForm(forms.ModelForm):
	"""Same four specialization checkboxes the clinic settings page uses."""

	specialization = forms.MultipleChoiceField(
		choices=Clinic.SPECIALIZATION_CHOICES,
		required=False,
		widget=forms.CheckboxSelectMultiple,
	)

	class Meta:
		model = Clinic
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		raw = (self.instance.specialization or '') if self.instance and self.instance.pk else ''
		self.initial['specialization'] = [part.strip() for part in raw.split(',') if part.strip()]

	def clean_specialization(self):
		selected = self.cleaned_data.get('specialization') or []
		return ', '.join(selected)


class SpecializationListFilter(admin.SimpleListFilter):
	title = 'specialization'
	parameter_name = 'specialization'

	def lookups(self, request, model_admin):
		return Clinic.SPECIALIZATION_CHOICES

	def queryset(self, request, queryset):
		if self.value():
			return queryset.filter(specialization__icontains=self.value())
		return queryset


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
	form = ClinicAdminForm
	list_display = (
		"clinic_name", "user", "city", "state", "specialization",
		"age_range", "accepts_heart_problems", "accepts_catheter", "is_verified"
	)
	search_fields = ("clinic_name", "city", "state", "user__username", "contact_email")
	list_filter = (
		SpecializationListFilter,
		"is_verified",
		"age_range",
		"accepts_heart_problems",
		"accepts_catheter",
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
		"patient", "clinic", "medical_record", "requested_clinic_type",
		"appointment_date", "appointment_time", "status", "created_at"
	)
	search_fields = (
		"patient__full_name", "clinic__clinic_name", "medical_record__main_diagnosis"
	)
	list_filter = ("status", "appointment_date", "clinic")
