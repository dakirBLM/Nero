from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("clinics", "0014_update_appointment_statuses"),
    ]

    operations = [
        migrations.AddField(
            model_name="clinic",
            name="clinic_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("general", "General Rehabilitation Clinic"),
                    ("specialized", "Specialized Center"),
                    ("hospital_based", "Hospital-Based Rehab Unit"),
                ],
                default="",
                max_length=50,
            ),
        ),
        migrations.AddField(
            model_name="clinic",
            name="continent",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="clinic",
            name="country",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="appointment",
            name="accommodation_review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Accommodation Review"),
                    ("not_required", "No Accommodation Requested"),
                    ("accepted_with", "Accepted With Accommodation"),
                    ("accepted_without", "Accepted Without Accommodation"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="medical_review_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending Medical Review"),
                    ("accepted", "Medical Record Accepted"),
                    ("rejected", "Medical Record Rejected"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="needs_accommodation",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="appointment",
            name="preferred_room_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("single", "Single Room"),
                    ("double", "Double Room"),
                    ("suite", "Suite"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="requested_clinic_type",
            field=models.CharField(blank=True, default="", max_length=50),
        ),
        migrations.AddField(
            model_name="appointment",
            name="requested_continent",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="appointment",
            name="requested_country",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="appointment",
            name="requested_service",
            field=models.CharField(blank=True, default="", max_length=200),
        ),
        migrations.AddField(
            model_name="appointment",
            name="travelers_count",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="appointment_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="appointment_time",
            field=models.TimeField(blank=True, null=True),
        ),
    ]
