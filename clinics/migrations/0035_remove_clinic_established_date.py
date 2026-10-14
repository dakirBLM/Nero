# Drop the full established date now that every row carries its year
# (backfilled from the date by 0034). Existing rows are populated by the
# RunPython step, so no one-off default is needed here.

import core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0034_clinic_established_year'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='clinic',
            name='established_date',
        ),
        migrations.AlterField(
            model_name='clinic',
            name='established_year',
            field=models.PositiveIntegerField(help_text='Year the clinic was established (e.g. 2015)', validators=[core.validators.validate_established_year]),
        ),
    ]
