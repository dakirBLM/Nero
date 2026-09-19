from datetime import date

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from clinics.forms import AppointmentForm
from clinics.models import Clinic
from patients.models import Patient, MedicalRecord
from recommendations.views import _medical_compatible_clinics


def _make_clinic(username, **overrides):
    user = User.objects.create_user(
        username, f'{username}@example.com', 'pw-test-12345', user_type='clinic'
    )
    data = dict(
        user=user,
        clinic_name=username.title(),
        description='d',
        address='a',
        city='c',
        state='s',
        zip_code='1',
        phone_number='1',
        contact_email=f'{username}@example.com',
        specialization='spec',
        established_date=date(2000, 1, 1),
    )
    data.update(overrides)
    return Clinic.objects.create(**data)


def _make_record(suffix='1', **overrides):
    user = User.objects.create_user(
        f'patient{suffix}', f'p{suffix}@example.com', 'pw-test-12345', user_type='patient'
    )
    patient = Patient.objects.create(user=user, full_name=f'Patient {suffix}', gender='M', phone=suffix)
    data = dict(
        patient=patient,
        first_name='F',
        last_name='L',
        gender='M',
        date_of_birth=date(1990, 1, 1),
        address='addr',
        country='C',
        height=170,
        weight=70,
        main_diagnosis='dx',
        injury_date=date(2020, 1, 1),
        movement_ability='independent',
        is_self_reliant=True,
        uses_tracheostomy_tube=False,
    )
    data.update(overrides)
    return MedicalRecord.objects.create(**data)


class SmartRecommendationCompatibilityTests(TestCase):
    """Smart Recommendations must honor the new clinic acceptance flags."""

    def setUp(self):
        self.accepting = _make_clinic('accepting')
        self.reject_trach = _make_clinic('notrach', accepts_tracheostomy_tube=False)
        self.reject_dependent = _make_clinic('nodep', accepts_dependent_patients=False)
        self.reject_bedridden = _make_clinic('nobed', accepts_bedridden_patients=False)

    def _ids(self, record):
        return {clinic.id for clinic in _medical_compatible_clinics(record)}

    def test_tracheostomy_patient_matches_accepting_clinic_only(self):
        record = _make_record('trach', uses_tracheostomy_tube=True)
        matched = self._ids(record)
        self.assertIn(self.accepting.id, matched)
        self.assertNotIn(self.reject_trach.id, matched)
        self.assertIn(self.reject_dependent.id, matched)
        self.assertIn(self.reject_bedridden.id, matched)

    def test_dependent_patient_matches_accepting_clinic_only(self):
        record = _make_record('dep', is_self_reliant=False)
        self.assertTrue(record.is_dependent_patient)
        matched = self._ids(record)
        self.assertIn(self.accepting.id, matched)
        self.assertNotIn(self.reject_dependent.id, matched)
        self.assertIn(self.reject_trach.id, matched)
        self.assertIn(self.reject_bedridden.id, matched)

    def test_bedridden_patient_matches_accepting_clinic_only(self):
        record = _make_record('bed', movement_ability='bedridden')
        self.assertTrue(record.is_bedridden_patient)
        matched = self._ids(record)
        self.assertIn(self.accepting.id, matched)
        self.assertNotIn(self.reject_bedridden.id, matched)
        self.assertIn(self.reject_trach.id, matched)
        self.assertIn(self.reject_dependent.id, matched)

    def test_healthy_patient_is_not_excluded_by_new_flags(self):
        record = _make_record('healthy')
        matched = self._ids(record)
        self.assertEqual(
            matched,
            {
                self.accepting.id,
                self.reject_trach.id,
                self.reject_dependent.id,
                self.reject_bedridden.id,
            },
        )

    def test_default_clinic_stays_compatible_with_all_new_conditions(self):
        record = _make_record(
            'all',
            uses_tracheostomy_tube=True,
            is_self_reliant=False,
            movement_ability='bedridden',
        )
        matched = self._ids(record)
        self.assertIn(self.accepting.id, matched)
        self.assertNotIn(self.reject_trach.id, matched)
        self.assertNotIn(self.reject_dependent.id, matched)
        self.assertNotIn(self.reject_bedridden.id, matched)

    def test_age_range_is_enforced_in_recommendations_and_booking(self):
        today = timezone.localdate()
        child_record = _make_record(
            'child',
            date_of_birth=date(today.year - 10, 1, 1),
        )
        adults_only = _make_clinic(
            'adultsonly',
            age_range=Clinic.AgeRange.ADULTS_ONLY,
        )

        self.assertNotIn(adults_only.id, self._ids(child_record))

        form = AppointmentForm(
            data={
                'medical_record': child_record.id,
                'appointment_date': today,
                'appointment_time': '10:00',
                'notes': '',
            },
            patient=child_record.patient,
            clinic=adults_only,
        )
        self.assertFalse(form.is_valid())
        self.assertIn('Clinic only treats adults.', form.errors['medical_record'])


class ClinicSearchAuthenticationTests(TestCase):
    def test_anonymous_user_is_redirected_to_login(self):
        response = self.client.get(reverse('search_clinics'))

        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('login'), response.url)
