from datetime import date

from django.test import TestCase
from django.urls import reverse
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


class SearchClinicsPageTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('seeker', 'seeker@example.com', 'pw-test-12345', user_type='patient')
        Patient.objects.create(user=self.user, full_name='Seeker', gender='F', phone='1')
        self.client.force_login(self.user)
        _, self.accepting = _make_clinic('accepting')
        _, self.declining = _make_clinic('declining')
        self.declining.accepts_tracheostomy_tube = False
        self.declining.save()

    def test_accepts_section_is_not_shown(self):
        response = self.client.get(reverse('search_clinics'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'name="needs_tracheostomy"')
        self.assertNotContains(response, 'name="needs_dependent"')
        self.assertNotContains(response, 'name="needs_bedridden"')

    def test_search_still_filters_by_remaining_fields(self):
        response = self.client.get(reverse('search_clinics'), {'q': 'Accepting'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([c.pk for c in response.context['clinics']], [self.accepting.pk])

    def test_legacy_accepts_parameters_are_ignored(self):
        response = self.client.get(reverse('search_clinics'), {'city': 'c', 'needs_tracheostomy': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            sorted(c.pk for c in response.context['clinics']),
            sorted([self.accepting.pk, self.declining.pk]),
        )


class PatientPendingAppointmentsTests(TestCase):
    """Fresh (pending) requests must be visible on the patient appointments
    page — otherwise the patient can never submit booking details while the
    clinic side says 'Awaiting patient response'."""

    def setUp(self):
        self.user = User.objects.create_user('booker', 'booker@example.com', 'pw-test-12345', user_type='patient')
        self.patient = Patient.objects.create(user=self.user, full_name='Booker', gender='M', phone='1')
        _, self.clinic = _make_clinic('bookable')
        self.record = MedicalRecord.objects.create(
            patient=self.patient, first_name='Book', last_name='Er', gender='M',
            date_of_birth=date(1990, 1, 1), address='a', country='C',
            height=170, weight=70, main_diagnosis='dx', injury_date=date(2020, 1, 1),
            movement_ability='independent',
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient, clinic=self.clinic, medical_record=self.record,
        )
        self.client.force_login(self.user)

    def test_pending_appointment_is_listed(self):
        response = self.client.get(reverse('patient_appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.appointment, list(response.context['appointments']))
        self.assertContains(response, 'submit-booking-details')

    def test_pending_status_filter_option_exists(self):
        response = self.client.get(reverse('patient_appointments'))
        values = [f['value'] for f in response.context['status_filters']]
        self.assertIn('pending', values)
        filtered = self.client.get(reverse('patient_appointments'), {'status': 'pending'})
        self.assertIn(self.appointment, list(filtered.context['appointments']))


class AppointmentActionModalTests(TestCase):
    """Cancel/pay/delete use the styled in-page modal, never native
    confirm(); the underlying POSTs still work."""

    def setUp(self):
        self.user = User.objects.create_user('actor', 'actor@example.com', 'pw-test-12345', user_type='patient')
        self.patient = Patient.objects.create(user=self.user, full_name='Actor', gender='M', phone='1')
        _, clinic = _make_clinic('modalclinic')
        self.record = MedicalRecord.objects.create(
            patient=self.patient, first_name='Ac', last_name='Tor', gender='M',
            date_of_birth=date(1990, 1, 1), address='a', country='C',
            height=170, weight=70, main_diagnosis='dx', injury_date=date(2020, 1, 1),
            movement_ability='independent',
        )
        self.appointment = Appointment.objects.create(
            patient=self.patient, clinic=clinic, medical_record=self.record,
        )
        self.client.force_login(self.user)

    def test_no_native_confirms_and_modal_present(self):
        response = self.client.get(reverse('patient_appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "confirm('")
        self.assertContains(response, 'action-modal')
        self.assertContains(response, 'openActionModal')
        self.assertContains(response, f'cancel-form-{self.appointment.id}')

    def test_cancel_post_still_works(self):
        response = self.client.post(reverse('cancel_appointment', args=[self.appointment.id]))
        self.assertEqual(response.status_code, 302)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, 'cancelled')

    def test_action_modal_fully_arabic(self):
        Appointment.objects.create(
            patient=self.patient, clinic=self.appointment.clinic,
            medical_record=self.record, status='waiting_for_payment',
        )
        response = self.client.get(reverse('patient_appointments'), HTTP_ACCEPT_LANGUAGE='ar')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        for arabic in ['إلغاء هذا الموعد؟', 'نعم، إلغاء', 'تأكيد الدفع؟', 'نعم، ادفع']:
            self.assertIn(arabic, content)
        for english in ['Cancel this appointment?', 'Yes, Cancel', 'Confirm payment?', 'Yes, Pay']:
            self.assertNotIn(english, content)
