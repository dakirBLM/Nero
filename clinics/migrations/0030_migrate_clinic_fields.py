# Data migration for the clinic field restructure ticket:
#   1. accepts_catheter (single) -> accepts_permanent_catheter + accepts_intermittent_catheter
#      (old True meant "accepts both kinds", so copy True to both; False stays False for both)
#   2. established_date -> established_year
#   3. free-text clinic_type / specialization / facilities_text -> ClinicType /
#      Specialization / Facility rows + M2M links (legacy text columns are kept).
# Reference tables are seeded with the 4 canonical clinic kinds plus the example
# facilities used in the sign-up form, so the new structured inputs are usable
# immediately. Safe to re-run (get_or_create + idempotent per-clinic sync).

from django.db import migrations


DEFAULT_KINDS = [
    'Convalescence',
    'Weight loss',
    'Musculoskeletal treatment',
    'Neurological treatment',
]

DEFAULT_FACILITIES = [
    'Therapy Pool',
    'Modern Gym',
    'Electrotherapy',
    'Ultrasound',
]


def _split_names(value):
    return [part.strip() for part in (value or '').split(',') if part.strip()]


def migrate_forward(apps, schema_editor):
    Clinic = apps.get_model('clinics', 'Clinic')
    ClinicType = apps.get_model('clinics', 'ClinicType')
    Specialization = apps.get_model('clinics', 'Specialization')
    Facility = apps.get_model('clinics', 'Facility')

    for name in DEFAULT_KINDS:
        ClinicType.objects.get_or_create(name=name)
        Specialization.objects.get_or_create(name=name)
    for name in DEFAULT_FACILITIES:
        Facility.objects.get_or_create(name=name)

    for clinic in Clinic.objects.all():
        # 1. Catheter split: old True == accepted both kinds.
        if clinic.accepts_catheter:
            clinic.accepts_permanent_catheter = True
            clinic.accepts_intermittent_catheter = True
        else:
            clinic.accepts_permanent_catheter = False
            clinic.accepts_intermittent_catheter = False

        # 2. Year from full date.
        if clinic.established_date and not clinic.established_year:
            clinic.established_year = clinic.established_date.year

        clinic.save()

        # 3. Free text -> structured rows (extra distinct values are kept via get_or_create).
        for token in _split_names(clinic.clinic_type):
            row, _ = ClinicType.objects.get_or_create(name=token)
            clinic.clinic_types.add(row)
        for token in _split_names(clinic.specialization):
            row, _ = Specialization.objects.get_or_create(name=token)
            clinic.specializations.add(row)
        for token in _split_names(clinic.facilities_text):
            row, _ = Facility.objects.get_or_create(name=token)
            clinic.facilities.add(row)


def migrate_backward(apps, schema_editor):
    Clinic = apps.get_model('clinics', 'Clinic')
    for clinic in Clinic.objects.all():
        # Restore the old combined flag from the split flags.
        clinic.accepts_catheter = bool(
            clinic.accepts_permanent_catheter or clinic.accepts_intermittent_catheter
        )
        clinic.save(update_fields=['accepts_catheter'])


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0029_clinictype_facility_specialization_and_more'),
    ]

    operations = [
        migrations.RunPython(migrate_forward, migrate_backward),
    ]
