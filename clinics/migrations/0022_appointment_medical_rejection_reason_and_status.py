from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0021_alter_clinic_clinic_type_multi'),
    ]

    operations = [
        migrations.AlterField(
            model_name='appointment',
            name='status',
            field=models.CharField(
                choices=[
                    ('pending', 'Pending'),
                    ('accepted', 'Accepted'),
                    ('awaiting_accommodation', 'Awaiting Accommodation Confirmation'),
                    ('payment_pending', 'Waiting for Payment'),
                    ('clinic_date_change_proposed', 'Clinic Proposed Different Dates'),
                    ('patient_date_change_requested', 'Patient Requested Different Dates'),
                    ('payed', 'Payed'),
                    ('rejected', 'Rejected'),
                    ('completed', 'Completed'),
                    ('cancelled', 'Cancelled'),
                ],
                default='pending',
                max_length=40,
            ),
        ),
        migrations.AddField(
            model_name='appointment',
            name='medical_rejection_reason',
            field=models.CharField(
                blank=True,
                choices=[
                    ('not_a_match', 'Not aligned with clinic specialization'),
                    ('capacity_unavailable', 'No clinical capacity in requested timeline'),
                    ('missing_information', 'Insufficient medical information'),
                    ('medical_complexity', 'Case complexity beyond current capability'),
                    ('safety_concerns', 'Patient safety concerns'),
                    ('other', 'Other'),
                ],
                default='',
                max_length=40,
            ),
        ),
    ]
