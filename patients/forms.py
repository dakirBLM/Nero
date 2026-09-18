from django import forms
from .models import Patient, MedicalRecord
from django.contrib.auth import get_user_model
from core.location_choices import COUNTRY_CHOICES, PHONE_CODE_CHOICES, normalize_phone_number, split_phone_number


class UserForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ['username', 'email']

class PatientForm(forms.ModelForm):
    profile_picture = forms.ImageField(required=False)
    class Meta:
        model = Patient
        fields = ['full_name', 'date_of_birth', 'gender', 'phone', 'profile_picture']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
        def clean_date_of_birth(self):
         date_of_birth = self.cleaned_data.get('date_of_birth')
         if date_of_birth:
            from datetime import date
            if date_of_birth > date.today():
                raise forms.ValidationError("Birth date cannot be in the future.")
         return date_of_birth

class MedicalRecordForm(forms.ModelForm):
    REQUIRED_TEXT_FIELDS = ('current_medications', 'allergies', 'previous_surgeries')

    country = forms.ChoiceField(
        choices=COUNTRY_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    mobile_country_code = forms.ChoiceField(
        choices=PHONE_CODE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    whatsapp_country_code = forms.ChoiceField(
        choices=PHONE_CODE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )

    class Meta:
        model = MedicalRecord
        fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth',
            'email', 'mobile_number', 'whatsapp_number',
            'address', 'country', 'height', 'weight',
            'main_diagnosis', 'injury_date', 'movement_ability',
            'current_medications', 'allergies', 'previous_surgeries',
            # Mobility aids
            'uses_wheelchair', 'uses_walker', 'uses_crutch', 'uses_electric_wheelchair',
            # General patient condition
            'bowel_control', 'urine_control', 'uses_permanent_catheter', 'uses_intermittent_catheter',
            'uses_medical_condom', 'uses_diapers', 'can_breathe_normally', 'can_eat_independently',
            'can_dress_independently', 'is_aware_and_cooperative', 'is_self_reliant',
            'uses_feeding_tube', 'uses_stool_tube', 'uses_urine_tube',
            # Medical conditions
            'has_bedsores', 'has_diabetes', 'uses_insulin', 'has_heart_problems',
            'has_high_blood_pressure', 'has_infectious_diseases', 'has_vein_thrombosis', 'has_depression',
            # Uploads
            'medical_reports', 'patient_movement_video']
        widgets = {
            'injury_date': forms.DateInput(attrs={'type': 'date'}),
            'current_medications': forms.Textarea(attrs={'rows': 3}),
            'allergies': forms.Textarea(attrs={'rows': 2}),
            'previous_surgeries': forms.Textarea(attrs={'rows': 3}),
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }
        labels = {
            'has_heart_problems': 'Heart Problems / مشاكل قلبية',
            'has_catheter': 'Catheter Usage / استخدام القسطرة',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name in self.REQUIRED_TEXT_FIELDS:
            self.fields[field_name].required = True

        if self.instance and self.instance.mobile_number:
            mobile_code, mobile_local = split_phone_number(self.instance.mobile_number)
            self.fields['mobile_country_code'].initial = mobile_code or '+1'
            self.fields['mobile_number'].initial = mobile_local

        if self.instance and self.instance.whatsapp_number:
            whatsapp_code, whatsapp_local = split_phone_number(self.instance.whatsapp_number)
            self.fields['whatsapp_country_code'].initial = whatsapp_code or '+1'
            self.fields['whatsapp_number'].initial = whatsapp_local

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.mobile_number = normalize_phone_number(
            self.cleaned_data.get('mobile_country_code'),
            self.cleaned_data.get('mobile_number'),
        )
        instance.whatsapp_number = normalize_phone_number(
            self.cleaned_data.get('whatsapp_country_code'),
            self.cleaned_data.get('whatsapp_number'),
        )
        if commit:
            instance.save()
        return instance

    def clean(self):
        cleaned_data = super().clean()
        for field_name in self.REQUIRED_TEXT_FIELDS:
            value = (cleaned_data.get(field_name) or '').strip()
            if not value:
                self.add_error(field_name, "This field is required. If not applicable, write 'I don't have any'.")
            else:
                cleaned_data[field_name] = value
        return cleaned_data