from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        # Import signals to register handlers
        try:
            import accounts.signals  # noqa: F401
            import accounts.social_signals  # noqa: F401
        except Exception:
            pass
