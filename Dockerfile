# ── Base image ────────────────────────────────────────────────
FROM python:3.11-slim

# Prevents Python from writing .pyc files and buffers stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# ── System dependencies ───────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# ── Working directory ─────────────────────────────────────────
WORKDIR /app

# ── Install Python dependencies ───────────────────────────────
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

# ── Copy project source ───────────────────────────────────────
COPY . .

# ── Collect static files ──────────────────────────────────────
# A throwaway key is supplied so settings.py (which now fails closed without a
# real SECRET_KEY) can load for this build-only step. The real keys are injected
# at runtime via the platform's environment, never baked into the image.
RUN SECRET_KEY="build-time-collectstatic-only" DEBUG=False \
    python manage.py collectstatic --noinput

# ── Expose port ───────────────────────────────────────────────
EXPOSE 8000

# ── Container healthcheck (hits the liveness endpoint) ────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/healthz' % os.environ.get('PORT','8000'))" || exit 1

# ── Run migrations, then start Gunicorn ───────────────────────
# PORT is provided by the host platform (Render/Fly/etc.); defaults to 8000.
CMD python manage.py migrate --noinput && \
    gunicorn Nero_platform.wsgi:application \
    --bind 0.0.0.0:${PORT:-8000} --workers ${WEB_CONCURRENCY:-1} --threads 4 --timeout 120 \
    --access-logfile - --error-logfile -
