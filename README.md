
# Nero

> A medical tourism platform connecting patients with clinics through medical-record management, clinic discovery, recommendations, appointments, messaging, and integrated services.

---

## Overview

**Nero** is a Django-based medical tourism platform designed to connect **patients** with **clinics**.

Patients can create and manage medical records, discover clinics based on their medical needs and treatment preferences, request appointments, communicate with clinics, and manage appointment-related information.

Clinics can create detailed profiles, publish services and content, manage patient requests and appointments, and communicate with patients.

The platform also includes clinic recommendation and matching logic, Google Calendar integration, medical-file storage, internationalization, and a Nero AI chat integration.

---

## Features

### Patient Features

* Create and manage a patient profile
* Create and update structured medical records
* Upload medical reports and movement videos
* Search for clinics
* Find clinics based on:

  * Medical compatibility
  * Country
  * Continent
  * Clinic type
  * Requested service
* View clinic profiles, services, facilities, and reviews
* Submit clinic and appointment requests
* Manage appointment information and treatment dates
* Handle accommodation requirements
* Track payment and appointment status
* Add appointments to Google Calendar
* Communicate with clinics through chat
* Create and manage posts
* Submit clinic reviews
* Use the Nero AI assistant
* Manage account and Google connection settings

### Clinic Features

* Create and manage a clinic profile
* Configure:

  * Specializations
  * Clinic type
  * Facilities
  * Languages
  * Patient age range
  * Patient-condition acceptance criteria
* Add clinic services and price ranges
* Manage a clinic image gallery
* Publish posts with images or videos
* Search and manage patient information
* Review patient medical records
* Accept or reject medical requests
* Propose alternative treatment dates
* Manage accommodation requests
* Set appointment/payment information
* Track appointment status
* Communicate with patients
* Add appointments to Google Calendar

### Clinic Recommendation

Nero provides a rule-based clinic matching flow.

The recommendation process:

1. The patient selects a medical record.
2. Clinics are filtered according to medical compatibility.
3. The patient can filter by continent, country, and clinic type.
4. The requested service is matched against clinic services and descriptions.
5. Clinics receive service-match points.
6. Matching clinics are displayed according to their match score.
7. Clinic ratings are also displayed with the results.

Medical compatibility is applied **before** service matching, so clinics that do not meet the relevant patient-condition requirements are filtered out first.

### Appointment Management

Appointments support a multi-stage workflow including:

* Pending
* Medical-record acceptance or rejection
* Accommodation decisions
* Proposed date changes
* Waiting for payment
* Paid
* Upcoming
* Cancelled

Appointments can contain treatment dates, requested services, accommodation information, payment information, and notes.

### Messaging

Nero provides two-user chat rooms between:

* Patient ↔ Patient
* Patient ↔ Clinic
* Clinic ↔ Clinic

Patient–clinic messaging is associated with appointment status. Conversations can become available when the relevant appointment is **paid or upcoming**.

Messages contain:

* Sender
* Content
* Timestamp
* Read/unread status

### Clinic Content

Clinics can publish posts containing:

* Text descriptions
* Images
* Videos

Clinics can also maintain:

* Profile pictures
* Cover photos
* Gallery images
* Services
* Service descriptions
* Service price ranges

### Medical Records & Files

Medical records contain structured information covering areas such as:

* Personal information
* Physical information
* Medical conditions
* Medications
* Allergies
* Previous surgeries
* Mobility
* Medical equipment
* General condition
* Contact information

Medical reports and movement videos have file-type and size restrictions and use dedicated medical-file storage.

> **Development note:** local development can use encrypted local storage for medical files. Production deployments can be configured to use private object storage.

### Google Calendar

Nero supports Google Calendar integration for appointments.

The application provides separate OAuth callback routes for patients and clinics:

```text
/clinics/google-calendar/callback/
/patients/google-calendar/callback/
```

Google Calendar credentials are optional for basic local development but are required for the Calendar integration.

### Nero AI

Nero includes an AI chat endpoint:

```text
/api/nero-ai/
```

The Django application sends AI requests to the configured `NERO_AI_WEBHOOK_URL`.

This means the AI functionality currently depends on an external webhook integration rather than a locally hosted AI model.

---

## User Roles

Nero currently defines two application-level user types:

| User type | Description                                                                                         |
| --------- | --------------------------------------------------------------------------------------------------- |
| `patient` | Creates medical records, searches for clinics, requests appointments, and communicates with clinics |
| `clinic`  | Manages clinic information, services, patient requests, appointments, and communication             |

The project also uses Django's built-in authentication and administration capabilities.

---

## Tech Stack

### Backend

* Python
* Django 4.2
* Django Allauth
* Django Extensions
* Django ORM
* Gunicorn

### Database

* SQLite for local development by default
* PostgreSQL supported for production deployments

### Security & Storage

* Argon2
* Cryptography / Fernet
* PyJWT
* Encrypted medical-file storage
* Django security features

### Frontend

The project uses Django templates alongside static frontend assets.

### Production Infrastructure

The repository includes configuration for:

* Docker
* Docker Compose
* Render
* PostgreSQL
* S3-compatible object storage
* WhiteNoise
* Sentry

---

## Project Structure

```text
Nero/
├── accounts/             # Authentication and user accounts
├── chat/                 # Chat rooms and messages
├── clinics/              # Clinic profiles, services and appointments
├── core/                 # Shared/core functionality
├── patients/             # Patient profiles and medical records
├── posts/                # Post-related functionality
├── recommendations/      # Clinic recommendation and matching
├── reviews/              # Clinic reviews
├── Nero_platform/        # Django project configuration
├── templates/            # HTML templates
├── static/               # Static assets
├── frontend/             # Frontend assets/components
├── scripts/              # Utility scripts
├── manage.py              # Django management entry point
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── Dockerfile             # Production/container image
├── docker-compose.yml     # Local Docker development
├── render.yaml            # Render deployment configuration
├── DEPLOY.md              # Deployment documentation
└── db.sqlite3             # Local SQLite database
```

---

# Local Development

## Prerequisites

For the standard local setup, you need:

* Python 3.11+
* Git
* pip
* A terminal

The Docker setup uses **Python 3.11**.

The application has also been tested locally with Python 3.12.3.

---

## 1. Clone the Repository

```bash
git clone https://github.com/dakirBLM/Nero.git
cd Nero
```

---

## 2. Create a Virtual Environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows:

```powershell
python -m venv .venv
.venv\Scripts\activate
```

After activation, your terminal should show the virtual environment name, for example:

```text
(.venv)
```

---

## 3. Install Dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The dependencies include Django, authentication packages, security libraries, database drivers, image processing, production server support, and storage integrations.

---

## 4. Configure Environment Variables

Create a local `.env` file from the provided example:

```bash
cp .env.example .env
```

For basic local development, keep:

```env
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
```

The development configuration can use built-in development fallbacks for `SECRET_KEY` and `ENCRYPTION_KEY`.

**Do not commit `.env` or production secrets to Git.**

---

## Environment Variables

### Django

```env
DEBUG=True
SECRET_KEY=
ENCRYPTION_KEY=
ALLOWED_HOSTS=127.0.0.1,localhost
CSRF_TRUSTED_ORIGINS=
SITE_ID=1
```

### Database

If `DATABASE_URL` is not configured, local development uses SQLite.

```env
DATABASE_URL=
```

For production, configure a PostgreSQL connection through `DATABASE_URL`.

### Private Medical Storage

Medical reports and movement videos can use local encrypted storage during development.

Production object storage can be configured using:

```env
PHI_S3_BUCKET=
PHI_S3_ENDPOINT_URL=
PHI_S3_ACCESS_KEY_ID=
PHI_S3_SECRET_ACCESS_KEY=
PHI_S3_REGION=
PHI_S3_ADDRESSING_STYLE=path
```

### Google OAuth

Used for optional social login:

```env
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
```

### Google Calendar

Used by the appointment Calendar integration:

```env
GOOGLE_CALENDAR_CLIENT_ID=
GOOGLE_CALENDAR_CLIENT_SECRET=
GOOGLE_CALENDAR_ID=primary
GOOGLE_CALENDAR_REDIRECT_BASE=
```

For local development, the Google Cloud OAuth application should include:

```text
http://localhost:8000/clinics/google-calendar/callback/
http://localhost:8000/patients/google-calendar/callback/
```

### Nero AI

The AI endpoint uses the `NERO_AI_WEBHOOK_URL` environment variable.

If the variable is not configured, the current application code contains a default webhook URL. For production deployments, configure the integration explicitly through the environment.

---

## 5. Run Database Migrations

```bash
python manage.py migrate
```

This creates/updates the database schema required by the Django applications.

For a fresh local installation using the default configuration, SQLite will be used.

---

## 6. Check the Project

Run Django's system checks:

```bash
DEBUG=True python manage.py check
```

A successful check should finish without errors.

---

## 7. Start the Development Server

```bash
DEBUG=True python manage.py runserver
```

The application will normally be available at:

```text
http://127.0.0.1:8000/
```

Open that address in your browser.

To stop the server:

```text
Ctrl+C
```

---

# Running with Docker

Docker provides an alternative local development environment.

## Prerequisites

Install:

* Docker
* Docker Compose

Create your local environment file:

```bash
cp .env.example .env
```

Then build and start Nero:

```bash
docker compose up --build
```

The Django development server will be available at:

```text
http://127.0.0.1:8000/
```

The Compose configuration:

* builds the application from the `Dockerfile`
* mounts the project for development
* persists the `media/` directory using a Docker volume
* exposes port `8000`
* loads `.env`
* runs Django with `DEBUG=True`

Stop the containers with:

```bash
docker compose down
```

---

# Testing

Run the Django test suite with:

```bash
DEBUG=True python manage.py test
```

A successful run should report all tests passing.

For example:

```text
Ran 18 tests
OK
```

The exact number of tests may change as the project evolves.

---

# Health Checks

Nero provides health endpoints through the core application.

### Liveness

```text
/healthz
```

### Readiness

```text
/readyz
```

These endpoints can be used by deployment platforms and monitoring systems to verify application availability.

The Docker image also uses `/healthz` for its container health check.

---

# Useful Routes

Some of the main application routes include:

| Area                    | Route                             |
| ----------------------- | --------------------------------- |
| Admin                   | `/admin/`                         |
| Login                   | `/accounts/login/`                |
| Patient dashboard       | `/patients/dashboard/`            |
| Patient medical records | `/patients/medical-records/`      |
| Patient appointments    | `/patients/appointments/`         |
| Clinic dashboard        | `/clinics/dashboard/`             |
| Clinic appointments     | `/clinics/appointments/`          |
| Chat                    | `/chat/`                          |
| Recommendations         | `/recommendations/questionnaire/` |
| Reviews                 | `/reviews/submit/<clinic_id>/`    |
| Nero AI                 | `/api/nero-ai/`                   |
| Health                  | `/healthz`                        |
| Readiness               | `/readyz`                         |

Routes may require authentication and/or a specific user type.

---

# Production & Deployment

The repository includes production-oriented configuration for containerized deployment.

The Docker image:

1. Installs Python dependencies.
2. Copies the application.
3. Collects static files.
4. Exposes port `8000`.
5. Provides a container health check.
6. Runs database migrations at startup.
7. Starts the application with Gunicorn.

The container uses:

```text
Nero_platform.wsgi:application
```

as the WSGI application.

Production configuration should provide environment variables through the hosting platform rather than committing secrets to the repository.

For detailed deployment information, see:

```text
DEPLOY.md
```

---

# Security Notes

Nero handles medical information and therefore requires particular care when configuring deployments.

### Development

Use:

```env
DEBUG=True
```

for local development only.

Development fallbacks for secrets are not intended for production.

### Production

Production deployments should:

* Set `DEBUG=False`.
* Provide a strong `SECRET_KEY`.
* Provide an appropriate `ENCRYPTION_KEY`.
* Configure production `ALLOWED_HOSTS`.
* Configure CSRF trusted origins where required.
* Use a production database.
* Configure private storage for medical/PHI files.
* Keep secrets in environment variables or the hosting platform's secret-management system.
* Avoid using real sensitive medical data during development or testing.

The repository's deployment documentation contains additional production and infrastructure guidance.

---

# Development Workflow

A typical development workflow is:

```bash
# Activate environment
source .venv/bin/activate

# Install/update dependencies
pip install -r requirements.txt

# Apply database changes
python manage.py migrate

# Run checks
DEBUG=True python manage.py check

# Run tests
DEBUG=True python manage.py test

# Start development server
DEBUG=True python manage.py runserver
```

When modifying the database models, create and apply migrations as appropriate:

```bash
python manage.py makemigrations
python manage.py migrate
```

---

# Troubleshooting

### `SECRET_KEY environment variable is required`

If Django is running with:

```env
DEBUG=False
```

provide a production `SECRET_KEY`.

For local development, use:

```env
DEBUG=True
```

---

### Database errors

Make sure migrations have been applied:

```bash
python manage.py migrate
```

If using the default local configuration, Django uses SQLite.

---

### Google Calendar does not work

Verify that:

1. Google Calendar credentials are configured.
2. The OAuth redirect URI is registered in Google Cloud.
3. The callback URL matches the configured application URL.

For local development, use:

```text
http://localhost:8000/clinics/google-calendar/callback/
http://localhost:8000/patients/google-calendar/callback/
```

---

### Nero AI does not respond

The AI endpoint depends on the configured external webhook integration.

Check that the `NERO_AI_WEBHOOK_URL` configuration is available and that the external service is reachable.

The AI service is not a locally hosted model inside this repository.

---

# Repository Documentation

Additional deployment documentation is available in:

```text
DEPLOY.md
```

The repository also contains:

```text
render.yaml
Dockerfile
docker-compose.yml
.env.example
```

which provide deployment, container, and environment configuration.

---

# Contributing

Before opening a pull request:

1. Run the Django system checks.
2. Run the test suite.
3. Verify the application locally.
4. Keep secrets and `.env` files out of commits.
5. Document significant configuration or behavior changes.
6. Keep the README updated when setup requirements change.

---

## License

No project license is currently documented in the repository. Add the appropriate license information here when one is selected.

---

## Status

Nero is under active development.

The available functionality, configuration, and deployment requirements may evolve as the platform continues to be developed.
