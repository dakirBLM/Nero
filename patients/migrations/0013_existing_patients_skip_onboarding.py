from django.db import migrations


def mark_existing_done(apps, schema_editor):
    """Existing patients shouldn't see the first-run tour — only new signups."""
    Patient = apps.get_model('patients', 'Patient')
    Patient.objects.update(onboarding_done=True)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('patients', '0012_patient_onboarding_done'),
    ]

    operations = [
        migrations.RunPython(mark_existing_done, noop),
    ]
