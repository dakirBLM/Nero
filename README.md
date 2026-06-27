![Nero](pic.png)

# Nero — Rehabilitation Care Platform

**Live Demo:** [https://haroune120.pythonanywhere.com/](https://haroune120.pythonanywhere.com/)

## What is Nero?
Nero is a simple web platform that connects **patients** with **rehabilitation clinics**. It makes it easy for patients to find the right care, and for clinics to manage and showcase their specialized services. 

Through Nero:
- **Patients** can search for clinics by specialty or location, upload their medical records securely, message clinics directly, and leave reviews.
- **Clinics** can create a detailed profile with their services, post updates, photos, and videos, and chat with interested patients.

---

## How to Run the Project Locally

Follow these simple steps to run the project on your own machine:

1. **Clone the repository and enter the directory:**
   ```bash
   git clone <repo-url>
   cd Nero_
   ```

2. **(Optional) Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install the required dependencies:**
   ```bash
   pip install -r requirements.txt
   ```


5. **Run database migrations:**
   ```bash
   python3 manage.py migrate
   ```

6. **Start the development server:**
   ```bash
   python3 manage.py runserver
   ```
   *The app will now be available at http://localhost:8000*

---

## Tech Stack & Security
- **Backend:** Django 4.2 (Python 3), SQLite

# Nero
# Nero
