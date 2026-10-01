from django.db import migrations


def merge_clinic_type_into_specialization(apps, schema_editor):
    """Keep any category that lived only on clinic_type before that column goes."""
    Clinic = apps.get_model('clinics', 'Clinic')
    for clinic in Clinic.objects.all().iterator():
        specializations = [part.strip() for part in (clinic.specialization or '').split(',') if part.strip()]
        extras = [
            part.strip()
            for part in (clinic.clinic_type or '').split(',')
            if part.strip() and part.strip() not in specializations
        ]
        if not extras:
            continue
        clinic.specialization = ', '.join(specializations + extras)
        clinic.save(update_fields=['specialization'])


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0031_remove_clinic_accepts_electric_wheelchair_and_more'),
    ]

    operations = [
        migrations.RunPython(merge_clinic_type_into_specialization, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name='clinic',
            name='clinic_type',
        ),
    ]
