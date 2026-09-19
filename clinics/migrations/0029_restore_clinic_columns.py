from django.db import migrations, models


# Columns that the reverted migration 0029_remove_clinic_accepts_electric_wheelchair_and_more
# dropped. That file no longer exists (PR #1 was reverted in PR #4), so the migration graph
# believes the fields were never removed while the deployed database has no columns for them.
# Every Clinic query therefore fails with UndefinedColumn until they are put back.
RESTORED_COLUMNS = (
    'number_of_therapists',
    'hours_of_operation',
    'facebook_url',
    'instagram_url',
    'linkedin_url',
    'accepts_electric_wheelchair',
)

# Name of the orphaned record left in django_migrations by the reverted migration.
ORPHANED_MIGRATION = '0029_remove_clinic_accepts_electric_wheelchair_and_more'


def restore_missing_columns(apps, schema_editor):
    """Add back only the columns that are actually absent.

    Databases created from scratch already have these columns from 0001/0004, so this has
    to stay idempotent — the test runner and any fresh deploy run this migration too.
    """
    Clinic = apps.get_model('clinics', 'Clinic')
    connection = schema_editor.connection

    with connection.cursor() as cursor:
        existing = {
            column.name
            for column in connection.introspection.get_table_description(
                cursor, Clinic._meta.db_table
            )
        }

    for column in RESTORED_COLUMNS:
        if column in existing:
            continue
        schema_editor.add_field(Clinic, Clinic._meta.get_field(column))


def drop_orphaned_migration_record(apps, schema_editor):
    """Forget the reverted migration so re-landing PR #1 would drop the columns again."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM django_migrations WHERE app = %s AND name = %s",
            ['clinics', ORPHANED_MIGRATION],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('clinics', '0028_alter_appointment_status_alter_clinic_phone_number_and_more'),
    ]

    operations = [
        # Database-only: the graph state already contains these fields, so declaring state
        # operations here would make makemigrations see a phantom change on every run.
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(
                    restore_missing_columns,
                    migrations.RunPython.noop,
                ),
                migrations.RunPython(
                    drop_orphaned_migration_record,
                    migrations.RunPython.noop,
                ),
            ],
            state_operations=[],
        ),
    ]
