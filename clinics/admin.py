from django import forms
from django.contrib import admin, messages
from django.shortcuts import redirect

from .models import (
	Clinic,
	ClinicGallery,
	ClinicService,
	Appointment,
	Specialization,
	get_specialization_choices,
	parse_specialization_names,
	specialization_in_use,
)


class ClinicAdminForm(forms.ModelForm):
	"""Specialization checkboxes driven by the Specialization table."""

	specialization = forms.MultipleChoiceField(
		choices=(),
		required=False,
		widget=forms.CheckboxSelectMultiple,
	)

	class Meta:
		model = Clinic
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		raw = (self.instance.specialization or '') if self.instance and self.instance.pk else ''
		existing = parse_specialization_names(raw)
		self.fields['specialization'].choices = get_specialization_choices(extra=existing)
		self.initial['specialization'] = existing

	def clean_specialization(self):
		selected = self.cleaned_data.get('specialization') or []
		return ', '.join(selected)


class SpecializationListFilter(admin.SimpleListFilter):
	title = 'specialization'
	parameter_name = 'specialization'

	def lookups(self, request, model_admin):
		return get_specialization_choices()

	def queryset(self, request, queryset):
		if self.value():
			return queryset.filter(specialization__icontains=self.value())
		return queryset


@admin.register(Specialization)
class SpecializationAdmin(admin.ModelAdmin):
	list_display = ("name", "clinics_using_it")
	search_fields = ("name",)

	def clinics_using_it(self, obj):
		target = obj.name.strip().lower()
		count = 0
		for value in Clinic.objects.exclude(specialization='').values_list('specialization', flat=True):
			if target in [part.lower() for part in parse_specialization_names(value)]:
				count += 1
		return count
	clinics_using_it.short_description = "Clinics using it"

	def delete_view(self, request, object_id, extra_context=None):
		obj = self.get_object(request, object_id)
		if obj is not None and specialization_in_use(obj.name):
			messages.error(request, f'Cannot delete "{obj.name}" because clinics still use it.')
			return redirect("admin:clinics_specialization_changelist")
		return super().delete_view(request, object_id, extra_context)

	def delete_queryset(self, request, queryset):
		blocked = [s.name for s in queryset if specialization_in_use(s.name)]
		if blocked:
			messages.error(request, f'Cannot delete in-use specializations: {", ".join(blocked)}.')
			queryset = queryset.exclude(name__in=blocked)
		return super().delete_queryset(request, queryset)


@admin.register(Clinic)
class ClinicAdmin(admin.ModelAdmin):
	form = ClinicAdminForm
	list_display = (
		"clinic_name", "user", "city", "state", "specialization",
		"established_year", "age_range", "is_verified",
		"accepts_heart_problems", "accepts_permanent_catheter", "accepts_intermittent_catheter",
		"accepts_wheelchair", "accepts_walker", "accepts_crutch",
		"accepts_bowel_incontinence", "accepts_urine_incontinence",
		"accepts_medical_condom", "accepts_diapers", "accepts_breathing_issues",
		"accepts_feeding_tube", "accepts_stool_tube", "accepts_urine_tube",
		"accepts_bedsores", "accepts_diabetes", "accepts_insulin",
		"accepts_high_blood_pressure", "accepts_infectious_diseases",
		"accepts_vein_thrombosis", "accepts_depression",
		"accepts_tracheostomy_tube", "accepts_dependent_patients", "accepts_bedridden_patients",
	)
	search_fields = ("clinic_name", "city", "state", "user__username", "contact_email")
	list_filter = (
		SpecializationListFilter,
		"is_verified",
		"age_range",
		"accepts_heart_problems", "accepts_permanent_catheter", "accepts_intermittent_catheter",
		"accepts_wheelchair", "accepts_walker", "accepts_crutch",
		"accepts_bowel_incontinence", "accepts_urine_incontinence",
		"accepts_medical_condom", "accepts_diapers", "accepts_breathing_issues",
		"accepts_feeding_tube", "accepts_stool_tube", "accepts_urine_tube",
		"accepts_bedsores", "accepts_diabetes", "accepts_insulin",
		"accepts_high_blood_pressure", "accepts_infectious_diseases",
		"accepts_vein_thrombosis", "accepts_depression",
		"accepts_tracheostomy_tube", "accepts_dependent_patients", "accepts_bedridden_patients",
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
