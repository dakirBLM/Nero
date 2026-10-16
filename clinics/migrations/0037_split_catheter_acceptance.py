from django.db import migrations, models


def copy_accepts_catheter(apps, schema_editor):
    Clinic = apps.get_model('clinics', 'Clinic')
    Clinic.objects.filter(accepts_catheter=False).update(
        accepts_permanent_catheter=False,
        accepts_intermittent_catheter=False,
    )


def restore_accepts_catheter(apps, schema_editor):
    Clinic = apps.get_model('clinics', 'Clinic')
    Clinic.objects.filter(
        accepts_permanent_catheter=False,
        accepts_intermittent_catheter=False,
    ).update(accepts_catheter=False)


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0036_merge_specialization_established_year'),
    ]

    operations = [
        migrations.AddField(
            model_name='clinic',
            name='accepts_permanent_catheter',
            field=models.BooleanField(default=True, help_text='Accept patients using a permanent catheter'),
        ),
        migrations.AddField(
            model_name='clinic',
            name='accepts_intermittent_catheter',
            field=models.BooleanField(default=True, help_text='Accept patients using an intermittent catheter'),
        ),
        migrations.RunPython(copy_accepts_catheter, restore_accepts_catheter),
        migrations.RemoveField(
            model_name='clinic',
            name='accepts_catheter',
        ),
    ]
