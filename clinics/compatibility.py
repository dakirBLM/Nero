from django.utils import timezone
from django.utils.translation import gettext as _

from .models import Clinic


SPECIAL_CARE_REQUIREMENTS = (
    ('uses_tracheostomy_tube', 'accepts_tracheostomy_tube'),
    ('is_dependent_patient', 'accepts_dependent_patients'),
    ('is_bedridden_patient', 'accepts_bedridden_patients'),
)


def medical_record_age(medical_record):
    """Return the patient's age from the medical record date of birth."""
    date_of_birth = getattr(medical_record, 'date_of_birth', None)
    if not date_of_birth:
        return None

    today = timezone.localdate()
    return (
        today.year
        - date_of_birth.year
        - ((today.month, today.day) < (date_of_birth.month, date_of_birth.day))
    )


def clinic_compatibility_errors(medical_record, clinic):
    """Return reasons why a medical record is incompatible with a clinic."""
    errors = []
    age = medical_record_age(medical_record)

    if age is not None:
        if age < 18 and clinic.age_range == Clinic.AgeRange.ADULTS_ONLY:
            errors.append(_('Clinic only treats adults.'))
        elif age >= 18 and clinic.age_range == Clinic.AgeRange.CHILDREN_ONLY:
            errors.append(_('Clinic only treats children.'))

    has_catheter = (
        getattr(medical_record, 'uses_permanent_catheter', False)
        or getattr(medical_record, 'uses_intermittent_catheter', False)
        or getattr(medical_record, 'uses_urine_tube', False)
    )
    rules = (
        (getattr(medical_record, 'has_heart_problems', False), 'accepts_heart_problems', _('Clinic does not accept patients with heart problems.')),
        (has_catheter, 'accepts_catheter', _('Clinic does not accept patients using a catheter.')),
        (getattr(medical_record, 'uses_wheelchair', False), 'accepts_wheelchair', _('Clinic does not accept patients using a wheelchair.')),
        (getattr(medical_record, 'uses_walker', False), 'accepts_walker', _('Clinic does not accept patients using a walker.')),
        (getattr(medical_record, 'uses_crutch', False), 'accepts_crutch', _('Clinic does not accept patients using crutches.')),
        (getattr(medical_record, 'uses_electric_wheelchair', False), 'accepts_electric_wheelchair', _('Clinic does not accept patients using an electric wheelchair.')),
        (not getattr(medical_record, 'bowel_control', True), 'accepts_bowel_incontinence', _('Clinic does not accept patients with bowel incontinence.')),
        (not getattr(medical_record, 'urine_control', True), 'accepts_urine_incontinence', _('Clinic does not accept patients with urine incontinence.')),
        (getattr(medical_record, 'uses_medical_condom', False), 'accepts_medical_condom', _('Clinic does not accept patients using a medical condom.')),
        (getattr(medical_record, 'uses_diapers', False), 'accepts_diapers', _('Clinic does not accept patients using diapers.')),
        (not getattr(medical_record, 'can_breathe_normally', True), 'accepts_breathing_issues', _('Clinic does not accept patients with breathing issues.')),
        (getattr(medical_record, 'uses_feeding_tube', False), 'accepts_feeding_tube', _('Clinic does not accept patients using a feeding tube.')),
        (getattr(medical_record, 'uses_stool_tube', False), 'accepts_stool_tube', _('Clinic does not accept patients using a stool tube.')),
        (getattr(medical_record, 'uses_urine_tube', False), 'accepts_urine_tube', _('Clinic does not accept patients using a urine tube.')),
        (getattr(medical_record, 'has_bedsores', False), 'accepts_bedsores', _('Clinic does not accept patients with bedsores.')),
        (getattr(medical_record, 'has_diabetes', False), 'accepts_diabetes', _('Clinic does not accept patients with diabetes.')),
        (getattr(medical_record, 'uses_insulin', False), 'accepts_insulin', _('Clinic does not accept patients using insulin.')),
        (getattr(medical_record, 'has_high_blood_pressure', False), 'accepts_high_blood_pressure', _('Clinic does not accept patients with high blood pressure.')),
        (getattr(medical_record, 'has_infectious_diseases', False), 'accepts_infectious_diseases', _('Clinic does not accept patients with infectious diseases.')),
        (getattr(medical_record, 'has_vein_thrombosis', False), 'accepts_vein_thrombosis', _('Clinic does not accept patients with vein thrombosis.')),
        (getattr(medical_record, 'has_depression', False), 'accepts_depression', _('Clinic does not accept patients with depression.')),
    )
    special_care_messages = (
        _('Clinic does not accept patients using a tracheostomy tube.'),
        _('Clinic does not accept dependent patients.'),
        _('Clinic does not accept bedridden patients.'),
    )
    special_care_rules = (
        (getattr(medical_record, record_field, False), clinic_field, message)
        for (record_field, clinic_field), message
        in zip(SPECIAL_CARE_REQUIREMENTS, special_care_messages)
    )

    for patient_has_condition, clinic_field, message in (*rules, *special_care_rules):
        if patient_has_condition and not getattr(clinic, clinic_field, False):
            errors.append(message)

    return errors


def is_clinic_compatible(medical_record, clinic):
    return not clinic_compatibility_errors(medical_record, clinic)
