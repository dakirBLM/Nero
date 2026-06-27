web: python manage.py migrate --noinput && gunicorn Nero_platform.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 120 --access-logfile - --error-logfile -
release: python manage.py migrate --noinput
