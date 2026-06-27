from django.db import migrations, models


class Migration(migrations.Migration):
    # Branch-duplicate of 0022_appointment_medical_rejection_reason_and_status:
    # both were generated from 0020 on parallel branches and add the SAME column.
    # Running the real ADD COLUMN twice fails on PostgreSQL ("column already exists")
    # even though SQLite tolerated it (it rebuilds the table). We keep this
    # migration's STATE change so the migration graph stays consistent, but make it a
    # no-op at the database level — 0022 performs the actual DDL.

    dependencies = [
        ('clinics', '0020_alter_appointment_status'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
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
            ],
        ),
    ]
