import os
from pathlib import Path

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / '.env')
except ImportError:
    # dotenv not available, skip loading .env file
    pass

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Core config (driven by environment; safe defaults for local dev) ──
# DEBUG defaults to False — production is the safe default. Set DEBUG=True
# in your local .env (never in production).
DEBUG = os.environ.get('DEBUG', 'False').strip().lower() in ('1', 'true', 'yes')

# SECRET_KEY MUST come from the environment in production. In local dev
# (DEBUG=True) we fall back to a clearly-insecure throwaway key so the app
# still runs without setup. Production refuses to boot without a real key.
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = 'django-insecure-dev-only-key-do-not-use-in-production'
    else:
        raise RuntimeError(
            'SECRET_KEY environment variable is required when DEBUG=False. '
            'Generate one with: python -c "from django.core.management.utils '
            'import get_random_secret_key as k; print(k())"'
        )
elif not DEBUG and SECRET_KEY.startswith('django-insecure-'):
    raise RuntimeError('Refusing to start in production with an insecure SECRET_KEY.')

# Dedicated key for encrypting medical-report files at rest (see
# patients/storage.py). Must be a Fernet key from Fernet.generate_key().
# Never derive this from SECRET_KEY in production.
ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')

# Comma-separated list of allowed hosts, e.g. "myapp.onrender.com,example.com"
ALLOWED_HOSTS = [
    h.strip() for h in os.environ.get(
        'ALLOWED_HOSTS',
        'haroune120.pythonanywhere.com,0.0.0.0,127.0.0.1,localhost',
    ).split(',') if h.strip()
]
# Always permit loopback so internal/container health probes (Docker HEALTHCHECK,
# `/healthz`) aren't rejected with HTTP 400 when ALLOWED_HOSTS is the public host.
for _loopback in ('127.0.0.1', 'localhost'):
    if _loopback not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_loopback)

# Trust the HTTPS origin(s) for CSRF (required once cookies are secured / behind HTTPS).
CSRF_TRUSTED_ORIGINS = [
    f'https://{h}' for h in ALLOWED_HOSTS
    if h and not h[0].isdigit() and h not in ('localhost',)
]
_extra_csrf = os.environ.get('CSRF_TRUSTED_ORIGINS', '').strip()
if _extra_csrf:
    CSRF_TRUSTED_ORIGINS += [o.strip() for o in _extra_csrf.split(',') if o.strip()]

# Render injects the real external hostname automatically — trust it so the app
# works without knowing the assigned *.onrender.com subdomain in advance.
_render_host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
if _render_host:
    if _render_host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_render_host)
    _render_origin = f'https://{_render_host}'
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google',
    'accounts',
    'patients',
    'clinics',
    'core',
    'chat',
    'posts',
    'reviews',
    'django_extensions',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'core.middleware.SessionUserIntegrityMiddleware',
    'core.middleware.RoleRouteGuardMiddleware',
    'allauth.account.middleware.AccountMiddleware',
    'accounts.middleware.BlockBlockedIPMiddleware',
    'core.middleware.LastSeenMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'Nero_platform.urls'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.total_unread',
            ],
        },
    },
]

# Database — DATABASE_URL (Postgres) in production; local SQLite fallback.
# Treat an UNSET *or EMPTY* DATABASE_URL as "use local SQLite": dj_database_url's
# default= only kicks in when the var is unset, not when it's a blank string.
import dj_database_url

_db_url = os.environ.get('DATABASE_URL', '').strip()
if _db_url:
    DATABASES = {'default': dj_database_url.parse(_db_url, conn_max_age=600)}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

# SQLite stopgap: a busy timeout so concurrent gunicorn workers don't instantly
# hit "database is locked". (No effect on Postgres — migrate before real traffic.)
if DATABASES['default']['ENGINE'] == 'django.db.backends.sqlite3':
    DATABASES['default'].setdefault('OPTIONS', {})['timeout'] = 20

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {'min_length': 8},
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

LANGUAGE_CODE = 'en'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Internationalization: English + Arabic (RTL)
LANGUAGES = [
    ('en', 'English'),
    ('ar', 'العربية'),
]
LOCALE_PATHS = [BASE_DIR / 'locale']

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]
# Destination for `collectstatic` (required for gunicorn/WhiteNoise to serve static).
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ── Storage ──────────────────────────────────────────────────
# Static: WhiteNoise compressed+hashed storage in production; plain storage in
# dev so `runserver` doesn't require a built manifest.
# Default (media): local filesystem for now — switch to object storage
# (django-storages + R2/Azure) before deploying to ephemeral hosting.
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "core.storage.ForgivingManifestStaticFilesStorage"
            if not DEBUG else
            "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

AUTH_USER_MODEL = 'accounts.User'
LOGIN_REDIRECT_URL = '/accounts/dashboard/'
LOGOUT_REDIRECT_URL = '/accounts/login/'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = int(os.getenv('SITE_ID', '1'))

ACCOUNT_LOGIN_REDIRECT_URL = '/accounts/dashboard/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/accounts/login/'

SOCIALACCOUNT_LOGIN_ON_GET = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION = True
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

# ── Email ─────────────────────────────────────────────────────
# Render (and most hosts) have no mail server, so Django's default SMTP-on-
# localhost:25 fails. When a provider's EMAIL_HOST is set (Brevo/Resend/Gmail/…)
# we send via SMTP; otherwise we print emails to the logs so password-reset and
# allauth signup-verification never crash the request.
BREVO_API_KEY = os.environ.get('BREVO_API_KEY', '')
if BREVO_API_KEY:
    # HTTPS API (port 443) — immune to SMTP port blocking on the host network.
    EMAIL_BACKEND = 'core.email_backend.BrevoAPIBackend'
elif os.environ.get('EMAIL_HOST'):
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = os.environ['EMAIL_HOST']
    EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
    EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').strip().lower() == 'true'
    EMAIL_USE_SSL = os.environ.get('EMAIL_USE_SSL', 'False').strip().lower() == 'true'
    EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
    EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
    # Never let a hung SMTP connection freeze a web request (misconfigured
    # host/port would otherwise block for minutes).
    EMAIL_TIMEOUT = int(os.environ.get('EMAIL_TIMEOUT', '10'))
else:
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'Nero <noreply@nero.app>')
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# allauth: build verification/reset links with the right scheme.
ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http' if DEBUG else 'https'

GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '').strip()
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '').strip()
GOOGLE_CALENDAR_CLIENT_ID = os.getenv('GOOGLE_CALENDAR_CLIENT_ID', '').strip()
GOOGLE_CALENDAR_CLIENT_SECRET = os.getenv('GOOGLE_CALENDAR_CLIENT_SECRET', '').strip()
GOOGLE_CALENDAR_ID = os.getenv('GOOGLE_CALENDAR_ID', 'primary').strip() or 'primary'
GOOGLE_CALENDAR_REDIRECT_BASE = os.getenv('GOOGLE_CALENDAR_REDIRECT_BASE', '').strip().rstrip('/')

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        },
    }
}

# Allow Google login without creating a SocialApp in Django admin.
if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
    SOCIALACCOUNT_PROVIDERS['google']['APP'] = {
        'client_id': GOOGLE_CLIENT_ID,
        'secret': GOOGLE_CLIENT_SECRET,
        'key': '',
    }

# Prefer Argon2 for password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
    'django.contrib.auth.hashers.ScryptPasswordHasher',
]

# ── SECURITY SETTINGS ────────────────────────────────────────
# Cookies are HTTPOnly + SameSite always; HTTPS-only is enforced in production.
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
CSRF_COOKIE_SAMESITE = 'Lax'

# In production (DEBUG=False) force HTTPS, secure cookies, and HSTS.
# In local dev (DEBUG=True) these stay off so plain HTTP keeps working.
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000  # 1 year
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    # The app runs behind a TLS-terminating proxy (PythonAnywhere/Render/etc.),
    # so trust the forwarded-proto header to detect HTTPS.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    # Don't 301-to-HTTPS the health endpoints, so plain-HTTP internal/container
    # probes get a 200 instead of a redirect.
    SECURE_REDIRECT_EXEMPT = [r'^healthz/?$', r'^readyz/?$']

# ── Logging ───────────────────────────────────────────────────
# Level is env-driven (LOG_LEVEL); console output is timestamped + structured.
# IMPORTANT (PHI): never log request bodies, chat messages, medical-report
# contents, emails, or IPs — log event names + anonymized user PKs only.
LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO' if DEBUG else 'WARNING').upper()
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[{asctime}] {levelname} {name}: {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': LOG_LEVEL,
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'accounts': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'patients': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'clinics': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
        'chat': {'handlers': ['console'], 'level': LOG_LEVEL, 'propagate': False},
    },
}

# ── Object storage (optional) ─────────────────────────────────
# When USE_S3_MEDIA=1, store uploads on an S3-compatible bucket (Supabase / R2 / S3)
# instead of local disk. Uploads always go through the S3 endpoint.
#
# How URLs are served (for <img> rendering) depends on S3_CUSTOM_DOMAIN:
#   • SET   → public bucket: URLs are the plain public object URL (no signing, no
#             expiry, browser-friendly). For Supabase set it to:
#             <ref>.supabase.co/storage/v1/object/public/<bucket>
#   • UNSET → private bucket: short-lived signed URLs.
if os.environ.get('USE_S3_MEDIA') == '1':
    _s3_opts = {
        'bucket_name': os.environ['S3_BUCKET'],
        'endpoint_url': os.environ.get('S3_ENDPOINT_URL') or None,
        'access_key': os.environ['S3_ACCESS_KEY_ID'],
        'secret_key': os.environ['S3_SECRET_ACCESS_KEY'],
        'region_name': os.environ.get('S3_REGION', 'auto'),
        'signature_version': 's3v4',
        # Supabase requires 'path'; Cloudflare R2 / AWS S3 use 'virtual'.
        'addressing_style': os.environ.get('S3_ADDRESSING_STYLE', 'virtual'),
        'file_overwrite': False,
    }
    _s3_custom_domain = os.environ.get('S3_CUSTOM_DOMAIN', '').strip().rstrip('/')
    if _s3_custom_domain:
        # Public bucket → serve via the public object URL (browser-friendly).
        _s3_opts['custom_domain'] = _s3_custom_domain
        _s3_opts['querystring_auth'] = False
    else:
        # Private bucket → short-lived signed URLs.
        _s3_opts['querystring_auth'] = True
        _s3_opts['querystring_expire'] = 900
        _s3_opts['default_acl'] = None
    STORAGES['default'] = {
        'BACKEND': 'storages.backends.s3.S3Storage',
        'OPTIONS': _s3_opts,
    }

# ── Error tracking (optional) ─────────────────────────────────
# Enabled when SENTRY_DSN is set. PHI-safe: no PII, request bodies/cookies scrubbed.
SENTRY_DSN = os.environ.get('SENTRY_DSN')
if SENTRY_DSN:
    import sentry_sdk

    def _scrub_phi(event, hint):
        req = event.get('request') or {}
        req.pop('data', None)
        req.pop('cookies', None)
        return event

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        send_default_pii=False,            # never attach user email/IP
        traces_sample_rate=0.0,            # stay within the free event budget
        environment=os.environ.get('ENV', 'production'),
        before_send=_scrub_phi,
    )