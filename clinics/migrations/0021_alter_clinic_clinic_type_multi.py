from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0020_alter_appointment_status'),
    ]

    operations = [
        migrations.AlterField(
            model_name='clinic',
            name='clinic_type',
            field=models.CharField(blank=True, default='', help_text='Selected clinic types (comma separated)', max_length=255),
        ),
    ]
