from django import forms
from patients.models import MedicalRecord
from .models import Appointment, Clinic, ClinicGallery, ClinicService
from accounts.forms import ClinicSignUpForm

class MedicalRecordChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self._clinic = kwargs.pop('clinic', None)
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        base = str(obj)
        notes = []
        if self._clinic:
            if getattr(obj, 'has_heart_problems', False) and not self._clinic.accepts_heart_problems:
                notes.append('clinic does not accept heart problems')
            has_catheter = (
                getattr(obj, 'uses_permanent_catheter', False)
                or getattr(obj, 'uses_intermittent_catheter', False)
                or getattr(obj, 'uses_urine_tube', False)
            )
            if has_catheter and not self._clinic.accepts_catheter:
                notes.append('clinic does not accept catheter')
        if notes:
            return f"{base} — ({'; '.join(notes)})"
        return base

class MedicalRecordSelect(forms.Select):
    def __init__(self, *args, **kwargs):
        self.disabled_values = set(str(v) for v in kwargs.pop('disabled_values', []))
        super().__init__(*args, **kwargs)

    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        option = super().create_option(name, value, label, selected, index, subindex=subindex, attrs=attrs)
        if value is not None and str(value) in self.disabled_values:
            option['attrs']['disabled'] = True
            # Optional: add a CSS class to style disabled options if needed
            option['attrs']['class'] = (option['attrs'].get('class', '') + ' option-disabled').strip()
            option['attrs']['title'] = 'Clinic does not accept this case'
        return option

class ClinicUpdateForm(forms.ModelForm):
    clinic_type = forms.MultipleChoiceField(
        choices=Clinic.CLINIC_TYPE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'clinic-type-checkbox'}),
        help_text="Select one or more clinic types"
    )

    class Meta:
        model = Clinic
        fields = [
            'clinic_name', 'tagline', 'description', 'address', 'city', 'state', 
            'country', 'continent', 'clinic_type', 'zip_code', 'phone_number', 'contact_email', 'website', 'google_maps_url', 'specialization', 
            'established_date', 'facilities', 
            'languages_spoken', 'hours_of_operation', 
            'profile_picture', 'cover_photo', 'facebook_url', 'instagram_url', 'linkedin_url',
            'accepts_heart_problems', 'accepts_catheter', 'accepts_wheelchair', 'accepts_walker', 'accepts_crutch',
            'accepts_electric_wheelchair', 'accepts_bowel_incontinence', 'accepts_urine_incontinence',
            'accepts_medical_condom', 'accepts_diapers', 'accepts_breathing_issues', 'accepts_feeding_tube',
            'accepts_stool_tube', 'accepts_urine_tube', 'accepts_bedsores', 'accepts_diabetes', 'accepts_insulin',
            'accepts_high_blood_pressure', 'accepts_infectious_diseases', 'accepts_vein_thrombosis', 'accepts_depression'
        ]
        widgets = {
            'established_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'hours_of_operation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'continent': forms.TextInput(attrs={'class': 'form-control'}),
            'zip_code': forms.TextInput(attrs={'class': 'form-control'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'contact_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'website': forms.URLInput(attrs={'class': 'form-control'}),
            'google_maps_url': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'https://www.google.com/maps/embed?pb=...'}),
            'specialization': forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            'languages_spoken': forms.TextInput(attrs={'class': 'form-control'}),
            'profile_picture': forms.FileInput(attrs={'class': 'form-control'}),
            'cover_photo': forms.FileInput(attrs={'class': 'form-control'}),
            'facebook_url': forms.URLInput(attrs={'class': 'form-control'}),
            'instagram_url': forms.URLInput(attrs={'class': 'form-control'}),
            'linkedin_url': forms.URLInput(attrs={'class': 'form-control'}),
            'accepts_heart_problems': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_catheter': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_wheelchair': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_walker': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_crutch': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_electric_wheelchair': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_bowel_incontinence': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_urine_incontinence': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_medical_condom': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_diapers': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_breathing_issues': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_feeding_tube': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_stool_tube': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_urine_tube': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_bedsores': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_diabetes': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_insulin': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_high_blood_pressure': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_infectious_diseases': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_vein_thrombosis': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_depression': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.clinic_type:
            selected_types = [t.strip() for t in self.instance.clinic_type.split(',') if t.strip()]
            self.fields['clinic_type'].initial = selected_types

        # Convert specialization field to MultipleChoiceField with CheckboxSelectMultiple widget
        self.fields['specialization'] = forms.MultipleChoiceField(
            choices=Clinic.SPECIALIZATION_CHOICES,
            required=False,
            widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
            help_text="Select one or more specializations"
        )
        # Parse comma-separated specializations into a list for the form
        if self.instance and self.instance.specialization:
            specializations = [s.strip() for s in self.instance.specialization.split(',')]
            self.fields['specialization'].initial = specializations
    
    def save(self, commit=True):
        clinic_types = self.cleaned_data.get('clinic_type', [])
        self.instance.clinic_type = ', '.join(clinic_types) if isinstance(clinic_types, list) else (clinic_types or '')

        # Preserve existing specialization if the field is omitted from submitted template.
        if 'specialization' in self.data:
            specializations = self.cleaned_data.get('specialization', [])
            self.instance.specialization = ', '.join(specializations) if isinstance(specializations, list) else specializations
        return super().save(commit=commit)

class ClinicGalleryForm(forms.ModelForm):
    class Meta:
        model = ClinicGallery
        fields = ['image', 'caption']
        widgets = {
            'image': forms.FileInput(attrs={'class': 'form-control'}),
            'caption': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Add a caption for this image...'
            }),
        }

class ClinicServiceForm(forms.ModelForm):
    class Meta:
        model = ClinicService
        fields = ['service_name', 'description', 'photo', 'price_range']
        widgets = {
            'service_name': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Describe this service in detail...'
            }),
            'photo': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*'}),
            'price_range': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., $100-$150 per session'
            }),
        }
        
class AppointmentForm(forms.ModelForm):
    class Meta:
        model = Appointment
        fields = ['medical_record', 'appointment_date', 'appointment_time', 'notes']
        widgets = {
            'appointment_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'appointment_time': forms.TimeInput(attrs={'type': 'time', 'class': 'form-control'}),
            'notes': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': 'Any specific requirements or notes for the clinic...'
            }),
            'medical_record': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):

        self.patient = kwargs.pop('patient', None)
        self.clinic = kwargs.pop('clinic', None)
        if self.clinic is None:
            raise ValueError("AppointmentForm requires a 'clinic' argument. None was provided.")
        super().__init__(*args, **kwargs)
        qs = MedicalRecord.objects.filter(patient=self.patient) if self.patient else MedicalRecord.objects.none()
        # Determine which records are incompatible for disabling in the select options
        disabled_ids = []
        for rec in qs:
            # Check all relevant fields
            incompatible = False
            if getattr(rec, 'has_heart_problems', False) and not self.clinic.accepts_heart_problems:
                incompatible = True
            if (
                getattr(rec, 'uses_permanent_catheter', False)
                or getattr(rec, 'uses_intermittent_catheter', False)
                or getattr(rec, 'uses_urine_tube', False)
            ) and not self.clinic.accepts_catheter:
                incompatible = True
            if getattr(rec, 'uses_wheelchair', False) and not self.clinic.accepts_wheelchair:
                incompatible = True
            if getattr(rec, 'uses_walker', False) and not self.clinic.accepts_walker:
                incompatible = True
            if getattr(rec, 'uses_crutch', False) and not self.clinic.accepts_crutch:
                incompatible = True
            if getattr(rec, 'uses_electric_wheelchair', False) and not self.clinic.accepts_electric_wheelchair:
                incompatible = True
            if not getattr(rec, 'bowel_control', True) and not self.clinic.accepts_bowel_incontinence:
                incompatible = True
            if not getattr(rec, 'urine_control', True) and not self.clinic.accepts_urine_incontinence:
                incompatible = True
            if getattr(rec, 'uses_medical_condom', False) and not self.clinic.accepts_medical_condom:
                incompatible = True
            if getattr(rec, 'uses_diapers', False) and not self.clinic.accepts_diapers:
                incompatible = True
            if not getattr(rec, 'can_breathe_normally', True) and not self.clinic.accepts_breathing_issues:
                incompatible = True
            if getattr(rec, 'uses_feeding_tube', False) and not self.clinic.accepts_feeding_tube:
                incompatible = True
            if getattr(rec, 'uses_stool_tube', False) and not self.clinic.accepts_stool_tube:
                incompatible = True
            if getattr(rec, 'uses_urine_tube', False) and not self.clinic.accepts_urine_tube:
                incompatible = True
            if getattr(rec, 'has_bedsores', False) and not self.clinic.accepts_bedsores:
                incompatible = True
            if getattr(rec, 'has_diabetes', False) and not self.clinic.accepts_diabetes:
                incompatible = True
            if getattr(rec, 'uses_insulin', False) and not self.clinic.accepts_insulin:
                incompatible = True
            if getattr(rec, 'has_high_blood_pressure', False) and not self.clinic.accepts_high_blood_pressure:
                incompatible = True
            if getattr(rec, 'has_infectious_diseases', False) and not self.clinic.accepts_infectious_diseases:
                incompatible = True
            if getattr(rec, 'has_vein_thrombosis', False) and not self.clinic.accepts_vein_thrombosis:
                incompatible = True
            if getattr(rec, 'has_depression', False) and not self.clinic.accepts_depression:
                incompatible = True
            if incompatible:
                disabled_ids.append(rec.pk)

        # Show all records; label indicates incompatibility; disable incompatible options
        self.fields['medical_record'] = MedicalRecordChoiceField(
            clinic=self.clinic,
            queryset=qs,
            widget=MedicalRecordSelect(attrs={'class': 'form-control'}, disabled_values=disabled_ids)
        )

    def clean_medical_record(self):
        record = self.cleaned_data.get('medical_record')
        clinic = self.clinic
        if record and clinic:
            # Check all relevant fields for incompatibility
            if getattr(record, 'has_heart_problems', False) and not clinic.accepts_heart_problems:
                raise forms.ValidationError('Clinic does not accept patients with heart problems.')
            if (
                getattr(record, 'uses_permanent_catheter', False)
                or getattr(record, 'uses_intermittent_catheter', False)
                or getattr(record, 'uses_urine_tube', False)
            ) and not clinic.accepts_catheter:
                raise forms.ValidationError('Clinic does not accept patients using a catheter.')
            if getattr(record, 'uses_wheelchair', False) and not clinic.accepts_wheelchair:
                raise forms.ValidationError('Clinic does not accept patients using a wheelchair.')
            if getattr(record, 'uses_walker', False) and not clinic.accepts_walker:
                raise forms.ValidationError('Clinic does not accept patients using a walker.')
            if getattr(record, 'uses_crutch', False) and not clinic.accepts_crutch:
                raise forms.ValidationError('Clinic does not accept patients using crutches.')
            if getattr(record, 'uses_electric_wheelchair', False) and not clinic.accepts_electric_wheelchair:
                raise forms.ValidationError('Clinic does not accept patients using an electric wheelchair.')
            if not getattr(record, 'bowel_control', True) and not clinic.accepts_bowel_incontinence:
                raise forms.ValidationError('Clinic does not accept patients with bowel incontinence.')
            if not getattr(record, 'urine_control', True) and not clinic.accepts_urine_incontinence:
                raise forms.ValidationError('Clinic does not accept patients with urine incontinence.')
            if getattr(record, 'uses_medical_condom', False) and not clinic.accepts_medical_condom:
                raise forms.ValidationError('Clinic does not accept patients using a medical condom.')
            if getattr(record, 'uses_diapers', False) and not clinic.accepts_diapers:
                raise forms.ValidationError('Clinic does not accept patients using diapers.')
            if not getattr(record, 'can_breathe_normally', True) and not clinic.accepts_breathing_issues:
                raise forms.ValidationError('Clinic does not accept patients with breathing issues.')
            if getattr(record, 'uses_feeding_tube', False) and not clinic.accepts_feeding_tube:
                raise forms.ValidationError('Clinic does not accept patients using a feeding tube.')
            if getattr(record, 'uses_stool_tube', False) and not clinic.accepts_stool_tube:
                raise forms.ValidationError('Clinic does not accept patients using a stool tube.')
            if getattr(record, 'uses_urine_tube', False) and not clinic.accepts_urine_tube:
                raise forms.ValidationError('Clinic does not accept patients using a urine tube.')
            if getattr(record, 'has_bedsores', False) and not clinic.accepts_bedsores:
                raise forms.ValidationError('Clinic does not accept patients with bedsores.')
            if getattr(record, 'has_diabetes', False) and not clinic.accepts_diabetes:
                raise forms.ValidationError('Clinic does not accept patients with diabetes.')
            if getattr(record, 'uses_insulin', False) and not clinic.accepts_insulin:
                raise forms.ValidationError('Clinic does not accept patients using insulin.')
            if getattr(record, 'has_high_blood_pressure', False) and not clinic.accepts_high_blood_pressure:
                raise forms.ValidationError('Clinic does not accept patients with high blood pressure.')
            if getattr(record, 'has_infectious_diseases', False) and not clinic.accepts_infectious_diseases:
                raise forms.ValidationError('Clinic does not accept patients with infectious diseases.')
            if getattr(record, 'has_vein_thrombosis', False) and not clinic.accepts_vein_thrombosis:
                raise forms.ValidationError('Clinic does not accept patients with vein thrombosis.')
            if getattr(record, 'has_depression', False) and not clinic.accepts_depression:
                raise forms.ValidationError('Clinic does not accept patients with depression.')
        return record