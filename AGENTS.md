# AGENTS.md

This file is for an AI agent changing the Nero Django app. Read the interview section and finish it before editing. The maps below are the place to look up where a feature lives and which data a change can break. Field names move between branches: read the model on the current branch before naming a field.

## Interview

A change starts when the user's message contains three answers:

1. **Files.** The files this change will touch. A list copied from the map is a proposal until the user confirms or corrects it.
2. **Kind.** One of: new feature, bug fix, or a change that can break an existing feature.
3. **Action.** What the person does in the product, in the user's words. Include who they are (patient, clinic, agency, or anonymous) and what they should see after the action.

Ask for every missing answer in one message, then stop. Put a proposed file list in that message when the map has a matching feature, and label it as a proposal. Code starts after the user confirms or corrects that list.

When the first message already contains all three, repeat them in one short block and edit only those files for that action.

A missing answer is a question, not a choice to fill in. Scope, files, and product behavior come from the user's answers.

The interview is done when the three answers are in the conversation and the file list matches what the user confirmed. The edit is done when only those files changed for that action.

## How to use the map

Find the feature row whose user action matches the request. Open every file in that row before proposing the list. If the change touches a row in Shared data, add every feature that lists that data to the proposal and say what can break. The user confirms which of those files are in scope.

`*/migrations/*.py` is schema history for that app. A model field change needs a new migration whose dependency is the current leaf. Clinics must keep a single leaf.

`*/tests.py` is the test module for that app. Include it only when the user confirms it.

## Shared data

| Data | Defined in | Used by |
| --- | --- | --- |
| `User` (`user_type` is `patient` or `clinic`) | `accounts/models.py` | Login, both dashboards, chat, posts, role guard |
| `BlockedIPRecord` | `accounts/models.py` | Login lockout |
| `Patient` | `patients/models.py` | Profile, settings, search, appointments, chat presence |
| `MedicalRecord`, `MedicalRecordReport`, `MedicalRecordVideo` | `patients/models.py` | Medical record form, clinic view of the record, booking checks, secure downloads |
| `Clinic`, `ClinicGallery`, `ClinicService` | `clinics/models.py` | Signup, settings, public page, search, recommendations |
| `Appointment` | `clinics/models.py` | Patient appointments, clinic appointments, agency appointments, recommendations send |
| `clinics.Post` and `posts.Post` | `clinics/models.py`, `posts/models.py` | Two different Post models. The interview names which one. |
| `ChatRoom`, `Message` | `chat/models.py` | Patient chat and clinic chat |
| `Review` | `reviews/models.py` | Stars and text on a clinic. `clinics/clinic_review_model.py` is a second review class; confirm it is the one in use before editing it. |

Clinic acceptance flags live on `Clinic`. Patient needs and abilities live on `MedicalRecord`. The link between them is `clinics/compatibility.py`. A new flag needs the model, the clinic forms, the medical-record form, this rules file, and the pages that render the flags. Ask which of those pages are in scope. Search is a separate page from the clinic profile.

## Feature map

### Landing and role choice

Anonymous visitor opens the site and picks patient or clinic.

| Files | Data |
| --- | --- |
| `core/views.py`, `core/urls.py` | none |
| `templates/landing_page.html`, `templates/choice_page.html`, `templates/base.html` | none |
| `templates/includes/site_nav.html`, `templates/includes/site_footer.html`, `templates/includes/header.html` | none |

Breaks: every page that extends `base.html`.

### Accounts, login, Google, password reset

A person logs in, logs out, resets a password, or starts Google sign-in as patient or clinic. After login, `dashboard_redirect` sends them to their own dashboard.

| Files | Data |
| --- | --- |
| `accounts/views.py`, `accounts/urls.py`, `accounts/forms.py` | `User` |
| `accounts/signals.py`, `accounts/social_signals.py` | `User`, `Patient` avatar |
| `accounts/emails.py`, `accounts/utils.py`, `accounts/middleware.py` | `User`, `BlockedIPRecord` |
| `accounts/admin.py`, `accounts/management/commands/view_blocked_ips.py` | `BlockedIPRecord` |
| `templates/accounts/login.html` and the `password_reset_*` templates | none |
| `templates/socialaccount/signup.html` | `User` |
| `templates/emails/welcome.html`, `templates/emails/welcome.txt` | `User` |

Breaks: both dashboards, the role guard in `core/middleware.py`, and any page that checks `user_type`.

### Patient profile, dashboard, settings

A logged-in patient opens the dashboard, settings, or their posts.

| Files | Data |
| --- | --- |
| `patients/views.py` (`patient_dashboard_view`, post views) | `Patient`, `MedicalRecord`, `Appointment`, posts |
| `patients/views_settings.py`, `patients/forms.py` | `Patient`, `User` |
| `patients/search_all.py` | `Patient`, `Clinic` |
| `templates/patient/dashboard/patient_dashboard.html` | dashboard feed |
| `templates/patient/dashboard/my_posts.html`, `templates/patient/dashboard/search_results.html` | posts, search hits |
| `templates/patient/patient_settings.html`, `templates/patient/signup.html` | `Patient`, `User` |
| `templates/includes/patient_nav.html` | header for patient pages |

Breaks: medical record, appointments, and chat unread counts shown on the dashboard.

### Medical record

A patient creates, edits, or downloads a record. A clinic opens that record from an appointment.

| Files | Data |
| --- | --- |
| `patients/views.py` (create, update, delete, see, secure download) | `MedicalRecord` and its files |
| `patients/forms.py`, `patients/storage.py` | same, encrypted storage |
| `patients/templatetags/file_extras.py` | file names in templates |
| `templates/patient/medical_record_form.html`, `medical_records.html`, `medical_record_success.html`, `see_medical_record.html` | the form and the patient's view |
| `templates/clinics/see_medical_record_clinic.html` | the clinic's view |
| `core/management/commands/sync_medical_media_to_private_bucket.py` | private bucket copy |

Breaks: `clinics/compatibility.py` and recommendation booking, because they read the same need and ability fields. Secure download URLs are also listed in `core/middleware.py` so a clinic may open them.

### Clinic signup, settings, and the two clinic pages

A clinic signs up or edits settings. Anyone can open the public clinic page (`clinic_detail`). The clinic opens its own page (`clinic_datils_clinic`; the URL name is spelled that way).

| Files | Data |
| --- | --- |
| `clinics/views.py` (signup, settings, both detail views, gallery, services) | `Clinic`, `ClinicGallery`, `ClinicService`, posts, `Review` |
| `clinics/forms.py`, `accounts/forms.py` (`ClinicSignUpForm`) | `Clinic` |
| `templates/clinics/signup.html`, `settings.html` | acceptance flags and profile fields |
| `templates/clinics/clinic_detail.html`, `clinic_datils_clinic.html` | public page and clinic page |
| `templates/clinics/clinic_services.html` | services |
| `clinics/admin.py` | the same `Clinic` fields in Django admin |

Breaks: search and recommendations, which read `Clinic` but do not share these templates. An anonymous visitor on either clinic page uses the header login control in those two templates only.

### Search

A patient searches clinics. A clinic searches patients. These pages are not the clinic profile.

| Files | Data |
| --- | --- |
| `patients/views.py` (`search_clinics_view`), `patients/search_all.py` | `Clinic`, `Patient` |
| `clinics/views.py` (`search_patients_view`, `search_patient_clinic_page`) | `Patient` |
| `templates/patient/search_clinics.html` | patient search |
| `templates/clinics/search_patients.html`, `search_patients_results.html`, `search_patient_clinic.html`, `search_clinics.html` | clinic-side search |
| `templates/includes/search_bar_styles.html` | search box styles |

Breaks: the header search on the dashboards and clinic pages, which calls `search_all` and `search_patients_for_clinic`.

### Recommendations and sending a request

A patient answers the questionnaire and sends appointment requests to clinics.

| Files | Data |
| --- | --- |
| `recommendations/views.py`, `recommendations/urls.py`, `recommendations/utils.py` | `Clinic`, `ClinicService`, `MedicalRecord`, `Appointment` |
| `clinics/compatibility.py` | medical-record needs checked against clinic flags |
| `templates/recommendations/questionnaire.html` | the form |

Breaks: appointment creation. A clinic that fails a compatibility rule must not receive a request. New acceptance flags belong in the clinic feature and in this rules file; ask before adding them to search.

### Appointments

A patient sees their appointments and can cancel, pay, delete, submit booking details, or answer a date proposal. The patient list hides `status='pending'`. A clinic, or the agency acting as that clinic, accepts the record, proposes dates, rejects, sets a payment, or marks the visit upcoming.

| Files | Data |
| --- | --- |
| `patients/views.py` (appointment actions and Google Calendar) | `Appointment`, `Patient` |
| `clinics/views.py` (clinic appointment actions and Google Calendar) | `Appointment`, `Clinic` |
| `clinics/access.py` | chooses the clinic: the logged-in clinic, or `clinic_id` for the agency |
| `clinics/templatetags/appointment_actions.py` | template tag that picks the clinic or agency URL |
| `patients/templatetags/appointment_filters.py` | appointment display filters |
| `templates/patient/appointments.html` | patient page, including the shared confirm dialog |
| `templates/clinics/clinic_appointments.html` | clinic page |
| `agency/urls.py` | the same clinic actions under `/agency/clinics/<clinic_id>/...` |

Breaks: the agency dashboard, because it reuses the clinic views. Status values live on `Appointment` in `clinics/models.py`. Adding a status means the model, both appointment templates, and the views that set that status.

### Chat

A patient or clinic opens a room and sends a message. Rooms start blocked until an admin unlocks them.

| Files | Data |
| --- | --- |
| `chat/views.py`, `chat/views_patient.py`, `chat/views_clinic.py`, `chat/urls.py` | `ChatRoom`, `Message`, `User` |
| `chat/admin.py` | unlock |
| `chat/templates/chat/chat_room_patient.html`, `chat_room_list_patient.html` | patient UI |
| `chat/templates/chat/chat_room_clinic.html`, `chat_room_list_clinic.html` | clinic UI |
| `chat/templates/chat/chat_room.html`, `chat_room_list.html` | shared room UI |

Breaks: unread badges on the patient and clinic headers.

### Posts

A patient or clinic creates, edits, or deletes a post from their dashboard. `posts/urls.py` has no routes; the dashboards own the actions. Confirm whether the change uses `clinics.models.Post` or `posts.models.Post`.

| Files | Data |
| --- | --- |
| `patients/views.py`, `clinics/views.py` | the Post model the user names |
| `posts/models.py`, `posts/admin.py`, `posts/views.py` | `posts.Post` |
| `templates/patient/dashboard/my_posts.html`, `templates/clinics/clinic_my_posts.html` | the lists |
| `posts/templates/posts/my_posts.html`, `posts/templates/posts/media_posts.html` | alternate post templates |

Breaks: the clinic detail pages, which render that clinic's posts.

### Reviews

A patient submits a star rating and text for a clinic.

| Files | Data |
| --- | --- |
| `reviews/views.py`, `reviews/urls.py`, `reviews/forms.py`, `reviews/models.py`, `reviews/admin.py` | `Review`, `Clinic`, `Patient` |
| Clinic detail templates | the public list of reviews |

Breaks: the rating shown on the clinic page and in recommendations.

### Nero AI

A logged-in user sends a chat message to the assistant at `POST /api/nero-ai/`.

| Files | Data |
| --- | --- |
| `patients/views.py` (`nero_ai_chat_api`) | the signed-in user and the request body |
| `Nero_platform/urls.py` | the route |

Breaks: the dashboard control that calls this URL.

### Agency

An agency user logs in with the agency password and works a clinic's appointments as that clinic.

| Files | Data |
| --- | --- |
| `agency/views.py`, `agency/urls.py`, `agency/auth.py`, `agency/emails.py` | `Clinic`, `Appointment`, `Patient` |
| `templates/agency/login.html`, `templates/agency/dashboard.html` | the agency screens |
| `templates/emails/patient_details.html`, `templates/emails/patient_details.txt` | the email the agency sends |
| `clinics/access.py`, `clinics/views.py` | the appointment actions |

Breaks: clinic appointment actions, because the agency URLs call those same functions.

### Admin, language, health

| Files | What it holds |
| --- | --- |
| `*/admin.py` | Django admin for that app |
| `locale/ar/LC_MESSAGES/django.po`, `django.mo` | Arabic strings. A new `{% trans %}` string is missing in Arabic until it is added here and the `.mo` is recompiled. |
| `core/views.py` `healthz`, `readyz` | deploy health checks |
| `templates/404.html`, `templates/500.html` | error pages |

### Platform, storage, and deploy

| Files | What it holds |
| --- | --- |
| `Nero_platform/settings.py` | installed apps, database, storage, login, middleware |
| `Nero_platform/urls.py` | root routes: admin, accounts, patients, clinics, chat, recommendations, posts, reviews, agency, Nero AI, language |
| `Nero_platform/wsgi.py`, `Nero_platform/asgi.py` | process entry |
| `manage.py` | Django commands |
| `core/middleware.py` | deleted-user logout, role guard, `last_seen` |
| `core/storage.py`, `core/azure_storage.py`, `patients/storage.py` | public media versus private medical files |
| `core/avatars.py` | default avatar |
| `core/email_backend.py` | outbound email |
| `core/validators.py`, `core/location_choices.py` | shared validation and country lists |
| `core/context_processors.py`, `core/file_cleanup_signals.py` | template context and file cleanup |
| `core/management/commands/upload_media.py` | media upload command |
| `accounts/middleware.py` | IP block middleware |
| `render.yaml`, `Dockerfile`, `docker-compose.yml`, `DEPLOY.md` | deploy |
| `.github/workflows/db-backup.yml` | database backup |
| `requirements.txt` | Python dependencies |
| `static/` | logos and images. `static/js/header-hide.js` hides the header on scroll. |
| `frontend/` | a separate React experiment. Django pages do not render it. |

## File catalog

One line per source file. Migrations are the `migrations/` folder inside each app.

### `accounts/`

| File | Holds |
| --- | --- |
| `models.py` | `User`, `BlockedIPRecord` |
| `views.py` | login, logout, Google start, dashboard redirect |
| `urls.py` | `/accounts/login/`, logout, dashboard, password reset |
| `forms.py` | login, signup, clinic signup, password reset |
| `admin.py` | user and blocked-IP admin |
| `emails.py` | welcome email send |
| `signals.py` | login failure and IP blocking |
| `social_signals.py` | Google profile and avatar sync |
| `middleware.py` | IP block during the request |
| `utils.py` | account helpers |
| `tests.py` | account tests |
| `management/commands/view_blocked_ips.py` | print blocked IPs |

### `patients/`

| File | Holds |
| --- | --- |
| `models.py` | `Patient`, `MedicalRecord`, report and video files |
| `views.py` | signup, dashboard, records, search, appointments, Nero AI, secure media |
| `views_settings.py` | patient settings and connect Google |
| `urls.py` | `/patients/...` routes |
| `forms.py` | medical record and patient forms |
| `search_all.py` | combined patient and clinic search |
| `storage.py` | encrypted medical file storage |
| `admin.py` | patient admin |
| `tests.py` | patient tests |
| `templatetags/appointment_filters.py` | appointment template filters |
| `templatetags/file_extras.py` | file template filters |

### `clinics/`

| File | Holds |
| --- | --- |
| `models.py` | `Clinic`, gallery, service, `Appointment`, and one `Post` |
| `views.py` | signup, dashboard, settings, both clinic pages, search, appointments |
| `urls.py` | `/clinics/...` routes. `clinic_datils_clinic` is the clinic's own page. |
| `forms.py` | clinic update and appointment forms |
| `admin.py` | clinic admin columns and filters |
| `compatibility.py` | rules that block a booking |
| `access.py` | clinic user versus agency user |
| `clinic_review_model.py` | a second review class; confirm before use |
| `tests.py` | clinic tests |
| `templatetags/appointment_actions.py` | clinic versus agency action URLs |

### `recommendations/`

| File | Holds |
| --- | --- |
| `views.py` | questionnaire, results, send requests |
| `urls.py` | `/recommendations/questionnaire/`, `result/`, `send-requests/` |
| `utils.py` | service and price matching |
| `tests.py` | recommendation and booking-rule tests |

### `chat/`

| File | Holds |
| --- | --- |
| `models.py` | `ChatRoom`, `Message` |
| `views.py` | start chat, send, mark read |
| `views_patient.py` | patient room list and room |
| `views_clinic.py` | clinic room list, room, unread count |
| `urls.py` | `/chat/...` |
| `admin.py` | unlock a room |
| `tests.py` | chat tests |
| `templates/chat/*.html` | room and room-list pages |

### `posts/`, `reviews/`, `agency/`, `core/`

| File | Holds |
| --- | --- |
| `posts/models.py` | the other `Post` |
| `posts/views.py` | no page routes |
| `posts/urls.py` | empty route list |
| `posts/admin.py` | post admin |
| `posts/tests.py` | post tests |
| `posts/templates/posts/*.html` | alternate post pages |
| `reviews/models.py` | `Review` |
| `reviews/views.py` | submit a review |
| `reviews/forms.py` | review form |
| `reviews/urls.py` | `/reviews/submit/<clinic_id>/` |
| `reviews/admin.py` | review admin |
| `reviews/tests.py` | review tests |
| `agency/views.py` | agency login, dashboard, send patient details |
| `agency/urls.py` | `/agency/` and appointment actions with `clinic_id` |
| `agency/auth.py` | agency session check |
| `agency/emails.py` | patient-details email |
| `agency/tests.py` | agency tests |
| `core/views.py` | landing, choice page, health checks |
| `core/urls.py` | `/`, `/choice_page`, `/healthz`, `/readyz` |
| `core/middleware.py` | session, role guard, last seen |
| `core/models.py` | empty |
| `core/admin.py` | core admin |
| `core/tests.py` | core tests |

### Templates

| File | Holds |
| --- | --- |
| `templates/landing_page.html`, `choice_page.html`, `base.html` | entry and shared layout |
| `templates/includes/header.html`, `site_nav.html`, `site_footer.html`, `patient_nav.html`, `search_bar_styles.html` | shared header, nav, search |
| `templates/accounts/*` | login and password reset |
| `templates/socialaccount/signup.html` | Google signup |
| `templates/patient/signup.html`, `patient_settings.html` | patient account pages |
| `templates/patient/dashboard/patient_dashboard.html` | patient dashboard |
| `templates/patient/dashboard/my_posts.html`, `search_results.html` | posts and dashboard search |
| `templates/patient/medical_record_form.html`, `medical_records.html`, `medical_record_success.html`, `see_medical_record.html` | medical record |
| `templates/patient/appointments.html` | patient appointments |
| `templates/patient/search_clinics.html` | clinic search |
| `templates/clinics/signup.html`, `settings.html` | clinic account pages |
| `templates/clinics/clinic_dashboard.html` | clinic dashboard |
| `templates/clinics/clinic_detail.html` | public clinic page |
| `templates/clinics/clinic_datils_clinic.html` | the clinic's own page |
| `templates/clinics/clinic_appointments.html` | clinic appointments |
| `templates/clinics/clinic_my_posts.html`, `clinic_services.html` | posts and services |
| `templates/clinics/patient_detail.html`, `see_medical_record_clinic.html` | one patient, one record |
| `templates/clinics/search_*.html` | clinic-side search |
| `templates/recommendations/questionnaire.html` | questionnaire |
| `templates/agency/login.html`, `dashboard.html` | agency |
| `templates/emails/welcome.*`, `patient_details.*` | email bodies |
| `templates/404.html`, `templates/500.html` | errors |

Each app also has `apps.py` and `__init__.py`. Those register the package. `chat/` has no `apps.py` in this tree.
