from django import forms
from patients.models import MedicalRecord
from .compatibility import clinic_compatibility_errors, is_clinic_compatible
from .models import Appointment, Clinic, ClinicGallery, ClinicService
from accounts.forms import ClinicSignUpForm
from core.location_choices import COUNTRY_CHOICES, PHONE_CODE_CHOICES, normalize_phone_number, split_phone_number

class MedicalRecordChoiceField(forms.ModelChoiceField):
    def __init__(self, *args, **kwargs):
        self._clinic = kwargs.pop('clinic', None)
        super().__init__(*args, **kwargs)

    def label_from_instance(self, obj):
        base = str(obj)
        notes = clinic_compatibility_errors(obj, self._clinic) if self._clinic else []
        if notes:
            return f"{base} — ({'; '.join(str(note) for note in notes)})"
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
    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    phone_country_code = forms.ChoiceField(
        choices=PHONE_CODE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
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
            'languages_spoken', 'hours_of_operation', 'age_range',
            'profile_picture', 'cover_photo', 'facebook_url', 'instagram_url', 'linkedin_url',
            'accepts_heart_problems', 'accepts_catheter', 'accepts_wheelchair', 'accepts_walker', 'accepts_crutch',
            'accepts_electric_wheelchair', 'accepts_bowel_incontinence', 'accepts_urine_incontinence',
            'accepts_medical_condom', 'accepts_diapers', 'accepts_breathing_issues', 'accepts_feeding_tube',
            'accepts_stool_tube', 'accepts_urine_tube', 'accepts_bedsores', 'accepts_diabetes', 'accepts_insulin',
            'accepts_high_blood_pressure', 'accepts_infectious_diseases', 'accepts_vein_thrombosis', 'accepts_depression',
            'accepts_tracheostomy_tube', 'accepts_dependent_patients', 'accepts_bedridden_patients',
        ]
        widgets = {
            'established_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'age_range': forms.RadioSelect(attrs={'class': 'form-check-input'}),
            'description': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'hours_of_operation': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'tagline': forms.TextInput(attrs={'class': 'form-control'}),
            'city': forms.TextInput(attrs={'class': 'form-control'}),
            'state': forms.TextInput(attrs={'class': 'form-control'}),
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
            'accepts_tracheostomy_tube': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_dependent_patients': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'accepts_bedridden_patients': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.clinic_type:
            selected_types = [t.strip() for t in self.instance.clinic_type.split(',') if t.strip()]
            self.fields['clinic_type'].initial = selected_types

        if self.instance and self.instance.phone_number:
            phone_code, local_number = split_phone_number(self.instance.phone_number)
            self.fields['phone_country_code'].initial = phone_code or '+1'
            self.fields['phone_number'].initial = local_number

        if self.instance and self.instance.country:
            self.fields['country'].initial = self.instance.country

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
        self.instance.phone_number = normalize_phone_number(
            self.cleaned_data.get('phone_country_code'),
            self.cleaned_data.get('phone_number'),
        )

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
        disabled_ids = [
            rec.pk for rec in qs if not is_clinic_compatible(rec, self.clinic)
        ]

        # Show all records; label indicates incompatibility; disable incompatible options
        self.fields['medical_record'] = MedicalRecordChoiceField(
            clinic=self.clinic,
            queryset=qs,
            widget=MedicalRecordSelect(attrs={'class': 'form-control'}, disabled_values=disabled_ids)
        )

    def clean_medical_record(self):
        record = self.cleaned_data.get('medical_record')
        if record and self.clinic:
            errors = clinic_compatibility_errors(record, self.clinic)
            if errors:
                raise forms.ValidationError(errors[0])
        return record
