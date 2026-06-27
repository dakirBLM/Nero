from datetime import date

from django.test import TestCase
from django.contrib.auth.models import AnonymousUser

from accounts.models import User
from patients.models import Patient, MedicalRecord
from patients.views import _can_access_medical_record
from clinics.models import Clinic, Appointment


def _make_clinic(username):
    user = User.objects.create_user(username, f'{username}@example.com', 'pw-test-12345', user_type='clinic')
    clinic = Clinic.objects.create(
        user=user, clinic_name=username.title(), description='d', address='a', city='c',
        state='s', zip_code='1', phone_number='1', contact_email=f'{username}@example.com',
        specialization='spec', established_date=date(2000, 1, 1),
    )
    return user, clinic


class MedicalRecordAccessTests(TestCase):
    """Locks the PHI access-control contract in _can_access_medical_record:
    only the owning patient, a clinic with a matching appointment, or staff."""

    def setUp(self):
        self.owner = User.objects.create_user('owner', 'owner@example.com', 'pw-test-12345', user_type='patient')
        self.owner_patient = Patient.objects.create(user=self.owner, full_name='Owner', gender='M', phone='1')

        self.other = User.objects.create_user('other', 'other@example.com', 'pw-test-12345', user_type='patient')
        Patient.objects.create(user=self.other, full_name='Other', gender='M', phone='2')

        self.record = MedicalRecord.objects.create(
            patient=self.owner_patient, first_name='F', last_name='L', gender='M',
            date_of_birth=date(1990, 1, 1), address='addr', country='C', height=170, weight=70,
            main_diagnosis='dx', injury_date=date(2020, 1, 1), movement_ability='independent',
        )

        self.clinic_user, self.clinic = _make_clinic('clinone')
        self.other_clinic_user, self.other_clinic = _make_clinic('clintwo')

        self.staff = User.objects.create_user('staff', 'staff@example.com', 'pw-test-12345',
                                              user_type='patient', is_staff=True)

    def test_owner_can_access(self):
        self.assertTrue(_can_access_medical_record(self.owner, self.record))

    def test_other_patient_cannot_access(self):
        self.assertFalse(_can_access_medical_record(self.other, self.record))

    def test_clinic_without_appointment_cannot_access(self):
        self.assertFalse(_can_access_medical_record(self.clinic_user, self.record))

    def test_clinic_with_matching_appointment_can_access(self):
        Appointment.objects.create(patient=self.owner_patient, clinic=self.clinic, medical_record=self.record)
        self.assertTrue(_can_access_medical_record(self.clinic_user, self.record))

    def test_unrelated_clinic_cannot_access_despite_existing_appointment(self):
        Appointment.objects.create(patient=self.owner_patient, clinic=self.clinic, medical_record=self.record)
        self.assertFalse(_can_access_medical_record(self.other_clinic_user, self.record))

    def test_staff_can_access(self):
        self.assertTrue(_can_access_medical_record(self.staff, self.record))

    def test_anonymous_cannot_access(self):
        self.assertFalse(_can_access_medical_record(AnonymousUser(), self.record))
