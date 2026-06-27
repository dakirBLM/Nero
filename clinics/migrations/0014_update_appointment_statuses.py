from django.db import migrations, models


def migrate_confirmed_to_accepted(apps, schema_editor):
    Appointment = apps.get_model("clinics", "Appointment")
    Appointment.objects.filter(status="confirmed").update(status="accepted")


class Migration(migrations.Migration):

    dependencies = [
        ("clinics", "0013_clinicservice_photo"),
    ]

    operations = [
        migrations.RunPython(migrate_confirmed_to_accepted, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("accepted", "Accepted"),
                    ("payed", "Payed"),
                    ("rejected", "Rejected"),
                    ("completed", "Completed"),
                    ("cancelled", "Cancelled"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
