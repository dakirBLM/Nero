from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatroom",
            name="is_messaging_blocked",
            field=models.BooleanField(
                default=True,
                help_text="Blocked by default. Admin unlocks this room after payment verification.",
            ),
        ),
        migrations.AddField(
            model_name="chatroom",
            name="unlocked_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
