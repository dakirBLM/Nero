# Joins the two 0034 leaves that landed independently:
# 0034_specialization (dynamic specializations) and
# 0034_clinic_established_year -> 0035_remove_clinic_established_date.

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0034_specialization'),
        ('clinics', '0035_remove_clinic_established_date'),
    ]

    operations = [
    ]
