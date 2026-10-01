
# Nero

Nero is a Django-based medical tourism platform that connects patients with clinics and healthcare providers. It provides patient and clinic accounts, medical-record management, clinic discovery, appointment management, recommendations, messaging, reviews, Google integrations, and an AI assistant.

---

## Table of Contents

* [Overview](#overview)
* [Features](#features)

  * [Patient Features](#patient-features)
  * [Clinic Features](#clinic-features)
  * [Recommendations](#recommendations)
  * [Chat and Messaging](#chat-and-messaging)
  * [Nero AI](#nero-ai)
  * [Authentication and Account Management](#authentication-and-account-management)
  * [Internationalization](#internationalization)
  * [Security and Storage](#security-and-storage)
* [Technology Stack](#technology-stack)
* [Project Structure](#project-structure)
* [Prerequisites](#prerequisites)
* [Local Installation](#local-installation)
* [Environment Configuration](#environment-configuration)
* [First Run](#first-run)
* [Running the Development Server](#running-the-development-server)
* [Docker](#docker)
* [Important Routes](#important-routes)
* [Appointment Statuses](#appointment-statuses)
* [File Upload Limits](#file-upload-limits)
* [Google Integration](#google-integration)
* [Media Storage](#media-storage)
* [Management Commands](#management-commands)
* [Health Checks](#health-checks)
* [Testing](#testing)
* [Troubleshooting](#troubleshooting)
* [Deployment](#deployment)
* [Frontend Prototype](#frontend-prototype)
* [Security Notes](#security-notes)
* [Contributing](#contributing)
* [License](#license)

---

# Overview

Nero is a web application built with Django 4.2 and Django REST Framework.

The platform supports two main user types:

* **Patients** — manage medical information, search for clinics, request appointments, communicate with clinics, and receive clinic recommendations.
* **Clinics** — manage clinic profiles, services, appointments, patients, posts, and communication.

The project also includes:

* Google authentication
* Google Calendar integration
* multilingual support
* Arabic RTL support
* password reset
* encrypted/private medical media handling
* clinic recommendations
* real-time-style presence/last-seen information
* unread message counts
* Nero AI assistant
* health/readiness endpoints
* automated database backup workflow

---

# Features

## Patient Features

Patients can:

* Create a patient account
* Log in and log out
* Reset their password
* Create and manage medical records
* Upload medical reports
* Upload movement videos
* Securely view/download medical media
* Search for clinics
* Filter clinics by location and clinic type
* Submit medical-tourism requests
* Receive clinic recommendations
* View clinic profiles
* View clinic services
* View clinic posts
* Request appointments
* Manage appointment information
* Confirm payments
* Add appointments to Google Calendar
* Respond to proposed appointment/date changes
* Cancel appointments
* Chat with clinics
* View unread messages
* See online/last-seen information
* Submit clinic reviews
* Create and manage patient posts
* Use the Nero AI assistant
* Switch between supported languages, including Arabic

Useful patient routes:

* [`/patients/signup/`](patients/urls.py)
* [`/patients/dashboard/`](patients/urls.py)
* [`/patients/medical-records/`](patients/urls.py)
* [`/patients/appointments/`](patients/urls.py)
* [`/patients/search-clinics/`](patients/urls.py)
* [`/recommendations/questionnaire/`](recommendations/urls.py)

---

## Clinic Features

Clinics can:

* Create a clinic account
* Manage their clinic profile
* Define clinic type and specialization
* Add clinic services
* Upload profile and cover images
* Manage gallery images
* Define accepted patient conditions
* Manage appointments
* Review patient medical information
* Accept or reject appointment requests
* Propose alternative dates
* Manage accommodation information
* Set payment amounts
* Mark appointments as upcoming
* Add appointments to Google Calendar
* Search for patients
* Communicate with patients
* View unread messages
* Track patient/clinic presence
* Create clinic posts
* Edit and delete posts
* Upload post images and videos

Clinic profile information can include:

* Clinic name
* Tagline
* Description
* Address
* City/state/country
* Contact information
* Website
* Google Maps location
* Specializations
* Clinic type
* Facilities
* Languages spoken
* Profile picture
* Cover photo
* Age range
* Patient-condition acceptance information

---

## Recommendations

Nero provides a clinic recommendation workflow for patients.

The recommendation process includes:

1. Selecting a medical record.
2. Selecting the requested service.
3. Selecting geographic preferences.
4. Selecting clinic types.
5. Filtering clinics according to medical compatibility.
6. Calculating service relevance.
7. Displaying matching clinics.

Medical compatibility is applied before service matching.

Clinics that do not satisfy the patient's required medical compatibility criteria are filtered out before the service-match calculation.

The service matching logic considers the clinic's services and descriptions.

Related implementation:

* [`recommendations/`](recommendations/)
* [`recommendations/urls.py`](recommendations/urls.py)

---

# Chat and Messaging

Nero includes messaging between users.

Supported chat functionality includes:

* Patient-clinic conversations
* User-to-user chat functionality
* Clinic-facing chat
* Patient-facing chat
* Message sending
* Marking messages as read
* Unread message counts
* Online/last-seen information

### Main chat routes

Patient chat:

* [`/chat/rooms/patient/`](chat/urls.py)
* `/chat/room/patient/<room_id>/`

Clinic chat:

* [`/chat/rooms/clinic/`](chat/urls.py)
* `/chat/room/clinic/<room_id>/`

General chat room:

* [`/chat/rooms/`](chat/urls.py)

> `/chat/` itself is not the main chat entry point. Use `/chat/rooms/` or the patient/clinic-specific routes.

---

# Nero AI

Nero includes an AI assistant that is available from the public landing page and can therefore be accessed by visitors without requiring a patient dashboard session.

The AI integration uses an external webhook rather than a locally hosted AI model.

## AI API endpoint

The Nero AI endpoint is:

```text
POST /api/nero-ai/
```

It expects JSON similar to:

```json
{
  "message": "What services does Nero provide?"
}
```

The endpoint is POST-only and protected by Django's CSRF mechanism.

The external AI service is configured through:

```text
NERO_AI_WEBHOOK_URL
```

The application should be configured with the appropriate webhook URL before relying on the AI functionality.

---

# Authentication and Account Management

Nero uses Django authentication with two main account types:

* `patient`
* `clinic`

Authentication functionality includes:

* Login
* Logout
* Patient registration
* Clinic registration
* Google authentication
* Password reset
* Dashboard redirection
* Google account connection

Authentication routes are defined in:

* [`accounts/urls.py`](accounts/urls.py)
* [`patients/urls.py`](patients/urls.py)
* [`clinics/urls.py`](clinics/urls.py)

Login:

```text
/accounts/login/
```

Password reset:

```text
/accounts/password-reset/
```

---

# Internationalization

Nero supports multiple languages and includes Arabic RTL support.

The project includes:

* Django internationalization
* English/Arabic language switching
* Arabic locale files
* RTL support
* Django's language-selection mechanism

Relevant project locations include:

* [`locale/`](locale/)
* [`core/`](core/)
* Django internationalization configuration in [`Nero_platform/settings.py`](Nero_platform/settings.py)

---

# Security and Storage

The application includes several security-related mechanisms.

These include:

* Django authentication
* CSRF protection
* Login-required views
* Role-based access restrictions
* Protected medical-record access
* Secure medical-media download/view endpoints
* Encrypted medical media handling
* Private media storage support
* IP-blocking middleware
* Security-related middleware
* Sentry integration support
* Environment-based secret configuration

Medical files should not be treated as ordinary public static files.

The application supports private media storage and encrypted medical media handling.

---

# Technology Stack

## Backend

* Python
* Django 4.2
* Django REST Framework
* Django Allauth
* SQLite for local development
* PostgreSQL support for deployment
* Gunicorn

## Frontend

The Django application uses:

* Django templates
* HTML
* CSS
* JavaScript

The repository also contains a separate React-based UI prototype under [`frontend/`](frontend/).

## Infrastructure

The project includes:

* Docker
* Docker Compose
* Render deployment configuration
* PostgreSQL support
* S3-compatible object storage support
* Sentry integration
* GitHub Actions workflows

---

# Project Structure

A simplified structure of the project is:

```text
Nero/
├── accounts/                 # Authentication and user accounts
├── chat/                    # Messaging and chat functionality
├── clinics/                 # Clinic profiles, services and appointments
├── core/                    # Shared utilities, validators and security
├── patients/                # Patient profiles, records and appointments
├── posts/                   # Post-related functionality
├── recommendations/         # Clinic recommendation system
├── reviews/                 # Clinic reviews
├── Nero_platform/           # Django project configuration
├── frontend/                # Standalone React/UI prototype
├── locale/                  # Translation files
├── scripts/                 # Utility scripts
├── templates/               # Django templates
├── static/                  # Static assets
├── media/                   # Local uploaded media
├── .github/
│   └── workflows/           # GitHub Actions workflows
├── .dockerignore
├── Dockerfile
├── docker-compose.yml
├── Procfile
├── index.html
├── manage.py
├── requirements.txt
├── .env.example
├── DEPLOY.md
└── README.md
```

### Important

`db.sqlite3` is generated locally after migrations and is not required to be present in a fresh clone.

The local database should not be committed to the repository.

---

# Prerequisites

For local development, install:

* Python 3.11+
* Git
* pip
* virtual environment support

Docker is optional if you prefer containerized development.

---

# Local Installation

## 1. Clone the repository

```bash
git clone <repository-url>
cd Nero
```

## 2. Create a virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

If PowerShell blocks script execution, use an appropriate Python environment activation method permitted by your Windows configuration.

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Copy the example environment file:

Linux/macOS:

```bash
cp .env.example .env
```

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

Windows Command Prompt:

```cmd
copy .env.example .env
```

Then edit `.env` and provide the required values.

> `.env` should be considered required for local development. Django defaults `DEBUG` to `False` when the variable is not explicitly configured, and the application requires a production secret key when running with `DEBUG=False`.

---

## 5. Run migrations

```bash
python manage.py migrate
```

This creates the local SQLite database when no external database URL is configured.

---

## 6. Check the Django project

```bash
python manage.py check
```

---

# Environment Configuration

The complete example configuration is available in:

[` .env.example`](.env.example)

Remove the extra space inside the link if your Markdown renderer does not accept it:

[`.env.example`](.env.example)

Important environment variables include:

## Django

```text
DEBUG
SECRET_KEY
ENCRYPTION_KEY
DATABASE_URL
```

When `DEBUG=True`, the project provides development fallbacks for some secrets.

Do not rely on development fallbacks in production.

---

## Nero AI

```text
NERO_AI_WEBHOOK_URL
```

This configures the external Nero AI webhook.

---

## Google Authentication

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
```

---

## Google Calendar

```text
GOOGLE_CALENDAR_CLIENT_ID
GOOGLE_CALENDAR_CLIENT_SECRET
GOOGLE_CALENDAR_REDIRECT_URI
```

---

## S3 / Object Storage

Depending on the storage configuration, the application can use:

```text
USE_S3_MEDIA
S3_BUCKET
S3_ENDPOINT_URL
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
S3_REGION
S3_ADDRESSING_STYLE
S3_CUSTOM_DOMAIN
```

Private medical media can also use:

```text
PHI_S3_BUCKET
PHI_S3_ENDPOINT_URL
PHI_S3_ACCESS_KEY_ID
PHI_S3_SECRET_ACCESS_KEY
PHI_S3_REGION
PHI_S3_ADDRESSING_STYLE
PHI_S3_CUSTOM_DOMAIN
```

The PHI-specific storage configuration can fall back to the corresponding general S3 settings when appropriate.

---

## Email

Email-related configuration includes:

```text
EMAIL_HOST
EMAIL_PORT
EMAIL_HOST_USER
EMAIL_HOST_PASSWORD
EMAIL_USE_TLS
EMAIL_USE_SSL
DEFAULT_FROM_EMAIL
BREVO_API_KEY
SITE_BASE_URL
```

For local development, email functionality may use Django's console email behavior, allowing password-reset/verification messages to be viewed in the terminal rather than sent externally.

---

## Monitoring

Optional Sentry configuration:

```text
SENTRY_DSN
```

---

## Other settings

The application also supports configuration such as:

```text
LOG_LEVEL
SERVE_MEDIA
SERVE_STATIC
```

Refer to [`Nero_platform/settings.py`](Nero_platform/settings.py) and [`.env.example`](.env.example) for the current configuration.

---

# First Run

After completing the installation steps, create an administrator account if administrative access is required:

```bash
python manage.py createsuperuser
```

Follow the prompts to create the account.

Then start the development server:

```bash
python manage.py runserver
```

Open:

```text
http://127.0.0.1:8000/
```

## Django Admin

The administration interface is available at:

```text
http://127.0.0.1:8000/admin/
```

Use the superuser account created with:

```bash
python manage.py createsuperuser
```

to access the Django admin.

---

## Creating a Patient Account

Patients can register through:

```text
/patients/signup/
```

After registration, the account can access the patient dashboard:

```text
/patients/dashboard/
```

---

## Creating a Clinic Account

Clinics can register through the clinic signup flow:

```text
/clinics/signup/
```

The application also provides a role-selection flow through:

```text
/choice_page
```

The exact UI flow may depend on the current authentication configuration.

---

# Running the Development Server

Start Django with:

```bash
python manage.py runserver
```

The application is normally available at:

```text
http://127.0.0.1:8000/
```

The `.env` file controls the development environment.

There is no need to prefix the command with:

```text
DEBUG=True
```

when `.env` already provides the development configuration.

This also makes the documented command compatible with Windows.

---

# Docker

The project includes both:

* [`Dockerfile`](Dockerfile)
* [`docker-compose.yml`](docker-compose.yml)

## Build and start the containers

```bash
docker compose up --build
```

The development Compose configuration runs Django on:

```text
http://127.0.0.1:8000/
```

## Important: run migrations

The Compose configuration overrides the image command with Django's development server, so migrations are not automatically executed by Compose.

After starting the containers, run:

```bash
docker compose exec web python manage.py migrate
```

If an administrator account is required:

```bash
docker compose exec web python manage.py createsuperuser
```

Then access:

```text
http://127.0.0.1:8000/
```

and:

```text
http://127.0.0.1:8000/admin/
```

---

# Important Routes

## General

| Purpose            | Route                       |
| ------------------ | --------------------------- |
| Landing page       | `/`                         |
| Login              | `/accounts/login/`          |
| Dashboard redirect | `/accounts/dashboard/`      |
| Password reset     | `/accounts/password-reset/` |
| Admin              | `/admin/`                   |
| Role selection     | `/choice_page`              |

## Patient

| Purpose         | Route                             |
| --------------- | --------------------------------- |
| Signup          | `/patients/signup/`               |
| Dashboard       | `/patients/dashboard/`            |
| Medical records | `/patients/medical-records/`      |
| Clinic search   | `/patients/search-clinics/`       |
| Appointments    | `/patients/appointments/`         |
| Recommendations | `/recommendations/questionnaire/` |

## Clinic

| Purpose        | Route                       |
| -------------- | --------------------------- |
| Signup         | `/clinics/signup/`          |
| Dashboard      | `/clinics/dashboard/`       |
| Appointments   | `/clinics/appointments/`    |
| Patient search | `/clinics/search-patients/` |
| Clinic posts   | `/clinics/my-posts/`        |

## Chat

| Purpose       | Route                  |
| ------------- | ---------------------- |
| Chat rooms    | `/chat/rooms/`         |
| Patient rooms | `/chat/rooms/patient/` |
| Clinic rooms  | `/chat/rooms/clinic/`  |

## Reviews

Clinic reviews are handled through the review application.

See:

[`reviews/urls.py`](reviews/urls.py)

## Health

```text
/healthz
/readyz
```

---

# Appointment Statuses

Appointments use the following status lifecycle:

```text
pending
accepted_record_accepted_accommodation
accepted_record_accommodation_change_requested
rejected_medical_record
cancelled
waiting_for_payment
paid
upcoming
```

### Meaning

* `pending` — appointment request has been submitted.
* `accepted_record_accepted_accommodation` — clinic accepted the medical record and requested accommodation arrangement.
* `accepted_record_accommodation_change_requested` — accommodation/date changes have been proposed.
* `rejected_medical_record` — clinic rejected the medical record.
* `cancelled` — appointment has been cancelled.
* `waiting_for_payment` — appointment is awaiting payment.
* `paid` — payment has been confirmed.
* `upcoming` — appointment is scheduled/upcoming.

Proposed dates are stored as appointment fields; they are not a separate appointment status.

---

# File Upload Limits

The application validates uploaded files according to their type.

## Medical reports

Supported formats include:

```text
PDF
JPG
PNG
```

Maximum size:

```text
3 MB
```

## Movement videos

Supported format:

```text
MP4
```

Maximum size:

```text
50 MB
```

## Clinic post videos

The video validator supports:

```text
mp4
webm
mov
m4v
```

The exact validation rules are implemented in:

[`core/validators.py`](core/validators.py)

---

# Google Integration

Nero supports Google authentication and Google Calendar integration.

## Google Authentication

The Google authentication flow uses Django Allauth.

The social authentication URL is mounted under:

```text
/accounts/social/
```

The Google OAuth callback is:

```text
http://localhost:8000/accounts/social/google/login/callback/
```

When configuring Google OAuth credentials for local development, make sure the redirect URI matches the callback path used by the application.

> Note: if [`DEPLOY.md`](DEPLOY.md) contains an older `/accounts/google/login/callback/` example, use the `/accounts/social/google/login/callback/` path used by the current application.

---

## Google Calendar

Patients and clinics can connect Google Calendar and add relevant appointments to their calendars.

Calendar callback routes are defined in:

* [`patients/urls.py`](patients/urls.py)
* [`clinics/urls.py`](clinics/urls.py)

Required Google Calendar credentials must be configured in `.env`.

---

# Media Storage

For local development, SQLite and local media storage can be used.

For deployment, Nero supports S3-compatible object storage.

General S3 settings include:

```text
USE_S3_MEDIA
S3_BUCKET
S3_ENDPOINT_URL
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
S3_REGION
S3_ADDRESSING_STYLE
S3_CUSTOM_DOMAIN
```

Private/PHI media can use the `PHI_S3_*` settings.

Relevant implementation:

* [`patients/storage.py`](patients/storage.py)
* [`Nero_platform/settings.py`](Nero_platform/settings.py)

---

# Management Commands

The project includes management commands for media synchronization and uploads.

Examples include:

```bash
python manage.py sync_medical_media_to_private_bucket
```

and:

```bash
python manage.py upload_media
```

Run:

```bash
python manage.py help
```

to see the management commands available in the current installation.

---

# Health Checks

Nero exposes two health-related endpoints.

## Health

```text
/healthz
```

This endpoint can be used to check whether the application is responding.

## Readiness

```text
/readyz
```

This endpoint checks application readiness.

These endpoints are also useful for deployment/container health checks.

---

# Testing

Run Django's test suite with:

```bash
python manage.py test
```

The current repository audit verified:

```text
18 tests
18 passed
```

You should rerun the test suite after making changes:

```bash
python manage.py test
```

Also run:

```bash
python manage.py check
```

before committing.

---

# Troubleshooting

## `SECRET_KEY environment variable is required`

Make sure `.env` exists and contains the required configuration.

```bash
cp .env.example .env
```

Then configure the required values.

---

## Database errors after cloning

The local SQLite database is generated through migrations.

Run:

```bash
python manage.py migrate
```

For Docker:

```bash
docker compose exec web python manage.py migrate
```

---

## No admin account

Create one with:

```bash
python manage.py createsuperuser
```

Then open:

```text
/admin/
```

---

## Google OAuth redirect error

Verify that the Google OAuth redirect URI matches the application's current callback:

```text
/accounts/social/google/login/callback/
```

Do not use an older `/accounts/google/login/callback/` path.

---

## AI assistant does not respond

Verify:

```text
NERO_AI_WEBHOOK_URL
```

is configured correctly.

The AI functionality depends on an external webhook and is not a local AI model.

---

## Docker database is empty

Run:

```bash
docker compose exec web python manage.py migrate
```

Then create an administrator if necessary:

```bash
docker compose exec web python manage.py createsuperuser
```

---

# Deployment

Deployment-specific information is available in:

[`DEPLOY.md`](DEPLOY.md)

The deployment configuration includes support for production-oriented services such as:

* PostgreSQL
* S3-compatible object storage
* Gunicorn
* Render
* Sentry

Review the deployment documentation and environment configuration before deploying.

---

# Frontend Prototype

The repository contains a [`frontend/`](frontend/) directory containing a standalone React/UI prototype.

This frontend is **not the build pipeline for the Django runtime application**.

The current Django application primarily renders:

* Django templates
* static CSS
* JavaScript

The React directory should therefore be treated as a separate UI/prototype area unless the project architecture is changed.

There is currently no required `npm install` / React build step for running the main Django application locally.

---

# GitHub Actions

The repository includes GitHub Actions workflows under:

[` .github/workflows/`](.github/workflows/)

These workflows include automated project tasks such as database backup operations.

Check the workflow files directly for the current triggers and configuration.

---

# Security Notes

## Environment secrets

Never commit:

```text
.env
```

or other files containing:

* secret keys
* passwords
* API keys
* OAuth secrets
* database credentials
* S3 credentials

Use `.env.example` as the configuration template.

---

## Database

`db.sqlite3` is a local development database and should not be committed.

It is generated after:

```bash
python manage.py migrate
```

---

## Medical data

Medical records and related media may contain sensitive information.

Use appropriate private storage and production security configuration when handling real patient data.

Do not upload real patient information to development environments or third-party services unless the required privacy, security, and compliance requirements have been reviewed.

---

## External AI service

The Nero AI assistant communicates with an external webhook configured through:

```text
NERO_AI_WEBHOOK_URL
```

Review the webhook provider's data-handling and privacy requirements before sending real patient information through the service.

---

# Contributing

Before opening a pull request:

1. Make sure the intended files are the only files changed.
2. Run Django checks:

```bash
python manage.py check
```

3. Run the tests:

```bash
python manage.py test
```

4. Check the Git diff:

```bash
git diff --check
```

5. Do not commit:

```text
.env
.venv/
db.sqlite3
```

6. Update documentation when application behavior or setup instructions change.

---

# License

No license is currently declared in the repository.

If a license is added, update this section and include the corresponding license file in the repository.
