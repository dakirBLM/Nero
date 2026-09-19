from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .models import Clinic

ADULT_AGE = 18

# (record fields signalling the need, clinic flag that must be on, refusal reason).
# A need is signalled when any of the record fields is true.
CONDITION_RULES = (
    (('has_heart_problems',), 'accepts_heart_problems', _('Clinic does not accept patients with heart problems.')),
    (('uses_permanent_catheter', 'uses_intermittent_catheter', 'uses_urine_tube'), 'accepts_catheter', _('Clinic does not accept patients using a catheter.')),
    (('uses_wheelchair',), 'accepts_wheelchair', _('Clinic does not accept patients using a wheelchair.')),
    (('uses_walker',), 'accepts_walker', _('Clinic does not accept patients using a walker.')),
    (('uses_crutch',), 'accepts_crutch', _('Clinic does not accept patients using crutches.')),
    (('uses_electric_wheelchair',), 'accepts_electric_wheelchair', _('Clinic does not accept patients using an electric wheelchair.')),
    (('uses_medical_condom',), 'accepts_medical_condom', _('Clinic does not accept patients using a medical condom.')),
    (('uses_diapers',), 'accepts_diapers', _('Clinic does not accept patients using diapers.')),
    (('uses_feeding_tube',), 'accepts_feeding_tube', _('Clinic does not accept patients using a feeding tube.')),
    (('uses_stool_tube',), 'accepts_stool_tube', _('Clinic does not accept patients using a stool tube.')),
    (('uses_urine_tube',), 'accepts_urine_tube', _('Clinic does not accept patients using a urine tube.')),
    (('uses_tracheostomy_tube',), 'accepts_tracheostomy_tube', _('Clinic does not accept patients using a tracheostomy tube.')),
    (('is_dependent_patient',), 'accepts_dependent_patients', _('Clinic does not accept dependent patients.')),
    (('is_bedridden_patient',), 'accepts_bedridden_patients', _('Clinic does not accept bedridden patients.')),
    (('has_bedsores',), 'accepts_bedsores', _('Clinic does not accept patients with bedsores.')),
    (('has_diabetes',), 'accepts_diabetes', _('Clinic does not accept patients with diabetes.')),
    (('uses_insulin',), 'accepts_insulin', _('Clinic does not accept patients using insulin.')),
    (('has_high_blood_pressure',), 'accepts_high_blood_pressure', _('Clinic does not accept patients with high blood pressure.')),
    (('has_infectious_diseases',), 'accepts_infectious_diseases', _('Clinic does not accept patients with infectious diseases.')),
    (('has_vein_thrombosis',), 'accepts_vein_thrombosis', _('Clinic does not accept patients with vein thrombosis.')),
    (('has_depression',), 'accepts_depression', _('Clinic does not accept patients with depression.')),
)

# Same shape, but the need is signalled when the ability is missing.
ABILITY_RULES = (
    ('bowel_control', 'accepts_bowel_incontinence', _('Clinic does not accept patients with bowel incontinence.')),
    ('urine_control', 'accepts_urine_incontinence', _('Clinic does not accept patients with urine incontinence.')),
    ('can_breathe_normally', 'accepts_breathing_issues', _('Clinic does not accept patients with breathing issues.')),
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


def _age_range_error(medical_record, clinic):
    age = medical_record_age(medical_record)
    if age is None:
        return None
    if age < ADULT_AGE and clinic.age_range == Clinic.AgeRange.ADULTS_ONLY:
        return _('Clinic only treats adults.')
    if age >= ADULT_AGE and clinic.age_range == Clinic.AgeRange.CHILDREN_ONLY:
        return _('Clinic only treats children.')
    return None


def clinic_compatibility_errors(medical_record, clinic):
    """Return reasons why a medical record is incompatible with a clinic."""
    errors = []

    age_range_error = _age_range_error(medical_record, clinic)
    if age_range_error:
        errors.append(age_range_error)

    needs = [
        (any(getattr(medical_record, field, False) for field in record_fields), clinic_field, message)
        for record_fields, clinic_field, message in CONDITION_RULES
    ]
    needs += [
        (not getattr(medical_record, record_field, True), clinic_field, message)
        for record_field, clinic_field, message in ABILITY_RULES
    ]

    for needs_support, clinic_field, message in needs:
        if needs_support and not getattr(clinic, clinic_field, False):
            errors.append(message)

    return errors


def is_clinic_compatible(medical_record, clinic):
    return not clinic_compatibility_errors(medical_record, clinic)
