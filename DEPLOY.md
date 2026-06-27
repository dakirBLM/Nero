# Nero — Deployment Guide (free-tier first)

Recommended $0 stack: **Render** (web) + **Neon** (Postgres) + **Cloudflare R2** (media).
> ⚠️ No free tier signs a HIPAA BAA. Use **synthetic/test data only** until you move PHI to a BAA-backed paid plan.

## 0. One-time local prep
```bash
# Recreate the venv (the committed one was broken/foreign) — Python 3.11+
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Generate the two production secrets (keep them OUT of the repo):
python -c "from django.core.management.utils import get_random_secret_key as k; print('SECRET_KEY=' + k())"
python -c "from cryptography.fernet import Fernet; print('ENCRYPTION_KEY=' + Fernet.generate_key().decode())"

# Sanity check
DEBUG=True python manage.py check
python manage.py test
```

Then init git and push to GitHub (the new `.gitignore` keeps `db.sqlite3`, `media/`, `.venv/`, `.env` out):
```bash
git init && git add -A && git status   # confirm no db.sqlite3 / media / .env staged
git commit -m "Production hardening + deploy scaffolding"
git remote add origin <your-github-repo> && git push -u origin main
```

## 1. Database — Neon (free Postgres)
1. Create a Neon project → copy the **pooled** connection string (host contains `-pooler`, ends with `?sslmode=require`).
2. You'll set it as the `DATABASE_URL` env var (step 3). Locally the app falls back to SQLite if unset.
3. Backups: Neon free keeps only 6h PITR — add a nightly `pg_dump "$DATABASE_URL" -Fc | gpg -c > backup.dump` shipped off-box.

## 2. Media — Cloudflare R2 (free, private)
1. Create a **private** R2 bucket `nero-media` (do NOT enable the `r2.dev` public URL).
2. Create an R2 API token (Object Read & Write) scoped to that bucket. Note Account ID, Access Key, Secret.
3. Set env vars: `USE_S3_MEDIA=1`, `S3_BUCKET=nero-media`, `S3_ENDPOINT_URL=https://<ACCOUNT_ID>.r2.cloudflarestorage.com`,
   `S3_ACCESS_KEY_ID=...`, `S3_SECRET_ACCESS_KEY=...`, `S3_REGION=auto`.
4. PHI is still served only through the existing ownership-checked views; signed URLs expire in 15 min.

## 3. App — Render (free web service)
Either use the included **`render.yaml`** Blueprint (New → Blueprint → pick repo) or a manual Web Service with:
- Build:  `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start:  `python manage.py migrate --noinput && gunicorn Nero_platform.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- Health check path: `/healthz`

Env vars to set in the dashboard:
| Var | Value |
|---|---|
| `DEBUG` | `False` |
| `SECRET_KEY` | (generated above) |
| `ENCRYPTION_KEY` | (generated above) |
| `ALLOWED_HOSTS` | `nero.onrender.com,yourdomain.com` |
| `CSRF_TRUSTED_ORIGINS` | `https://nero.onrender.com` |
| `DATABASE_URL` | (Neon pooled string) |
| `USE_S3_MEDIA` + `S3_*` | (from step 2) |
| `SENTRY_DSN` | optional |

## 4. OAuth
Add the production callback URLs to your Google Cloud OAuth client and update the allauth Site domain:
`https://<host>/accounts/google/login/callback/`, `.../patients/google-calendar/callback/`, `.../clinics/google-calendar/callback/`.

## 5. Verify live
- `https://<host>/healthz` → `ok`; `/readyz` → `{"status":"ready"}`
- Trigger a test error → confirm Sentry event has no email/IP/body.
- Log in, open a chat, upload + view a medical report.

## Migrating existing SQLite data (PHI-safe)
```bash
# from old sqlite (DATABASE_URL unset):
python manage.py dumpdata --natural-primary --natural-foreign \
  -e contenttypes -e auth.permission -e sessions.session -e admin.logentry -o /tmp/nero.json
# point DATABASE_URL at Neon, then:
python manage.py loaddata /tmp/nero.json && rm -P /tmp/nero.json   # shred — contains PHI
```
Media files were Fernet-encrypted under the OLD key; decrypt-then-reupload to R2 (don't copy ciphertext).
