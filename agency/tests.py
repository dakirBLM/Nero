import shutil
import tempfile
from datetime import date
from unittest import mock

from cryptography.fernet import Fernet
from django.core import mail
from django.core.files.base import ContentFile
from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import User
from clinics.models import Appointment, Clinic
from core.email_backend import _attachment_payload
from patients.models import MedicalRecord, Patient

from .auth import SESSION_KEY

PASSWORD = 'unit-test-agency-pw'
ACCEPTED = {
    'status': 'accepted_record_accepted_accommodation',
    'medical_record_accepted': True,
    'treatment_start_date': date(2030, 1, 10),
    'treatment_end_date': date(2030, 1, 20),
}


def _make_clinic(username):
    user = User.objects.create_user(username, f'{username}@example.com', 'pw-test-12345', user_type='clinic')
    return Clinic.objects.create(
        user=user, clinic_name=username.title(), description='d', address='a', city='c',
        state='s', zip_code='1', phone_number='1', contact_email=f'{username}@example.com',
        specialization='spec', established_date=date(2000, 1, 1),
    )


def _make_appointment(clinic, suffix='1', **overrides):
    user = User.objects.create_user(f'patient{suffix}', f'p{suffix}@example.com', 'pw-test-12345', user_type='patient')
    patient = Patient.objects.create(user=user, full_name=f'Patient {suffix}', gender='M', phone='1')
    record = MedicalRecord.objects.create(
        patient=patient, first_name='Ana', last_name=f'Test{suffix}', gender='F',
        date_of_birth=date(1990, 1, 1), address='addr', country='C', height=170, weight=70,
        main_diagnosis='dx', injury_date=date(2020, 1, 1), movement_ability='independent',
    )
    return Appointment.objects.create(patient=patient, clinic=clinic, medical_record=record, **overrides)


@override_settings(AGENCY_DASHBOARD_PASSWORD=PASSWORD)
class AgencyAuthTests(TestCase):
    def test_dashboard_requires_password(self):
        response = self.client.get(reverse('agency_dashboard'))
        self.assertRedirects(response, f"{reverse('agency_login')}?next={reverse('agency_dashboard')}")

    def test_wrong_password_is_rejected(self):
        response = self.client.post(reverse('agency_login'), {'password': 'nope'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Incorrect password')
        self.assertFalse(self.client.session.get(SESSION_KEY))

    def test_correct_password_unlocks_and_follows_next(self):
        target = reverse('agency_dashboard') + '?status=pending'
        response = self.client.post(reverse('agency_login') + f'?next={target}', {'password': PASSWORD, 'next': target})
        self.assertRedirects(response, target)
        self.assertTrue(self.client.session.get(SESSION_KEY))

    def test_logout_locks_again(self):
        self.client.post(reverse('agency_login'), {'password': PASSWORD})
        self.client.post(reverse('agency_logout'))
        self.assertFalse(self.client.session.get(SESSION_KEY))
        self.assertEqual(self.client.get(reverse('agency_dashboard')).status_code, 302)

    def test_logged_in_clinic_user_is_not_agency(self):
        clinic = _make_clinic('clinicx')
        self.client.force_login(clinic.user)
        self.assertEqual(self.client.get(reverse('agency_dashboard')).status_code, 302)
        self.assertEqual(self.client.get(reverse('agency_clinic_appointments', args=[clinic.id])).status_code, 302)


@override_settings(
    AGENCY_DASHBOARD_PASSWORD=PASSWORD,
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ENCRYPTION_KEY=Fernet.generate_key().decode(),
)
class AgencyDashboardTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.clinic_a = _make_clinic('alpha')
        self.clinic_b = _make_clinic('beta')
        self.pending = _make_appointment(self.clinic_a, '1')
        self.accepted = _make_appointment(self.clinic_b, '2', **ACCEPTED)
        self.client.post(reverse('agency_login'), {'password': PASSWORD})

    def test_dashboard_lists_every_clinic_with_counts(self):
        response = self.client.get(reverse('agency_dashboard'))
        self.assertContains(response, 'Alpha')
        self.assertContains(response, 'Beta')
        self.assertContains(response, reverse('agency_clinic_appointments', args=[self.clinic_a.id]))
        clinics = {c.id: c for c in response.context['clinics']}
        self.assertEqual(clinics[self.clinic_a.id].pending_count, 1)
        self.assertEqual(clinics[self.clinic_b.id].accepted_count, 1)
        self.assertEqual(response.context['total_appointments'], 2)

    def test_status_filter_narrows_recent_appointments(self):
        response = self.client.get(reverse('agency_dashboard') + '?status=pending')
        self.assertEqual([a.id for a in response.context['appointments']], [self.pending.id])

    def test_clinic_appointments_page_in_agency_mode(self):
        response = self.client.get(reverse('agency_clinic_appointments', args=[self.clinic_a.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['agency_mode'])
        self.assertEqual(response.context['clinic'], self.clinic_a)
        self.assertContains(response, reverse('agency_accept_medical_record', args=[self.clinic_a.id, self.pending.id]))
        self.assertNotContains(response, 'Message Patient')
        self.assertContains(response, reverse('agency_update_appointment_status', args=[self.clinic_a.id, self.pending.id]))

    def test_accepted_card_offers_send_details_instead_of_payment(self):
        response = self.client.get(reverse('agency_clinic_appointments', args=[self.clinic_b.id]))
        self.assertContains(response, reverse('agency_send_patient_details', args=[self.clinic_b.id, self.accepted.id]))
        self.assertNotContains(response, reverse('agency_set_payment_amount', args=[self.clinic_b.id, self.accepted.id]))
        self.assertContains(response, 'value="beta@example.com"')

    def test_agency_can_accept_medical_record_for_a_clinic(self):
        url = reverse('agency_accept_medical_record', args=[self.clinic_a.id, self.pending.id])
        response = self.client.post(url)
        self.assertRedirects(response, reverse('agency_clinic_appointments', args=[self.clinic_a.id]))
        self.pending.refresh_from_db()
        self.assertTrue(self.pending.medical_record_accepted)

    def test_agency_can_force_status(self):
        url = reverse('agency_update_appointment_status', args=[self.clinic_a.id, self.pending.id])
        self.client.post(url, {'status': 'cancelled'})
        self.pending.refresh_from_db()
        self.assertEqual(self.pending.status, 'cancelled')

    def test_appointment_must_belong_to_url_clinic(self):
        url = reverse('agency_accept_medical_record', args=[self.clinic_b.id, self.pending.id])
        self.assertEqual(self.client.post(url).status_code, 404)

    def test_agency_can_open_medical_record_and_files(self):
        record = self.pending.medical_record
        record.medical_reports.save('report.txt', ContentFile(b'report body'), save=True)
        page = self.client.get(reverse('see_medical_record_view', args=[record.id]) + f'?clinic_id={self.clinic_a.id}')
        self.assertEqual(page.status_code, 200)
        self.assertTemplateUsed(page, 'clinics/see_medical_record_clinic.html')
        self.assertContains(page, reverse('agency_clinic_appointments', args=[self.clinic_a.id]))
        download = self.client.get(reverse('secure_medical_report_download', args=[record.id]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b''.join(download.streaming_content), b'report body')

    def test_send_patient_details_email_with_attachment(self):
        record = self.accepted.medical_record
        record.medical_reports.save('mri.pdf', ContentFile(b'%PDF-1.4 fake'), save=True)
        url = reverse('agency_send_patient_details', args=[self.clinic_b.id, self.accepted.id])
        response = self.client.post(url, {'email': 'doctor@example.com'}, follow=True)
        self.assertRedirects(response, reverse('agency_clinic_appointments', args=[self.clinic_b.id]))
        self.assertContains(response, 'sent to doctor@example.com')

        self.assertEqual(len(mail.outbox), 1)
        message = mail.outbox[0]
        self.assertEqual(message.to, ['doctor@example.com'])
        self.assertIn('Ana Test2', message.subject)
        self.assertIn('Main diagnosis: dx', message.body)
        html = message.alternatives[0][0]
        self.assertIn('Booking request', html)
        self.assertIn('Beta', html)
        self.assertEqual([a[0] for a in message.attachments], ['mri.pdf'])
        self.assertEqual(message.attachments[0][1], b'%PDF-1.4 fake')

    def test_send_patient_details_rejects_bad_email(self):
        url = reverse('agency_send_patient_details', args=[self.clinic_b.id, self.accepted.id])
        self.client.post(url, {'email': 'not-an-email'})
        self.assertEqual(len(mail.outbox), 0)

    def test_oversized_file_is_listed_instead_of_attached(self):
        record = self.accepted.medical_record
        record.medical_reports.save('huge.bin', ContentFile(b'x' * 64), save=True)
        url = reverse('agency_send_patient_details', args=[self.clinic_b.id, self.accepted.id])
        with mock.patch('agency.emails.ATTACHMENT_BUDGET', 10), \
                mock.patch('agency.emails._read_decrypted', side_effect=AssertionError('file was read')):
            response = self.client.post(url, {'email': 'doctor@example.com'}, follow=True)
        self.assertContains(response, 'huge.bin (too large to attach)')
        self.assertEqual(mail.outbox[0].attachments, [])
        self.assertIn('huge.bin', mail.outbox[0].body)

    def test_decoded_size_skips_when_storage_under_reports(self):
        record = self.accepted.medical_record
        record.medical_reports.save('border.bin', ContentFile(b'x' * 64), save=True)
        url = reverse('agency_send_patient_details', args=[self.clinic_b.id, self.accepted.id])
        with mock.patch('agency.emails.ATTACHMENT_BUDGET', 10), \
                mock.patch('agency.emails._stored_size', return_value=1):
            response = self.client.post(url, {'email': 'doctor@example.com'}, follow=True)
        self.assertContains(response, 'border.bin (too large to attach)')
        self.assertEqual(mail.outbox[0].attachments, [])


class BrevoAttachmentPayloadTests(TestCase):
    def test_tuple_attachments_are_base64_encoded(self):
        message = mail.EmailMessage('s', 'b', to=['x@example.com'])
        message.attach('a.txt', b'hello', 'text/plain')
        self.assertEqual(_attachment_payload(message), [{'name': 'a.txt', 'content': 'aGVsbG8='}])


class ClinicUserFlowStillWorksTests(TestCase):
    """The shared views must keep behaving exactly the same for a logged-in clinic."""

    def setUp(self):
        self.clinic = _make_clinic('gamma')
        self.appointment = _make_appointment(self.clinic, '9')
        self.client.force_login(self.clinic.user)

    def test_clinic_page_not_in_agency_mode(self):
        response = self.client.get(reverse('clinic_appointments'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['agency_mode'])
        self.assertContains(response, reverse('accept_medical_record', args=[self.appointment.id]))
        self.assertNotContains(response, 'agency_send_patient_details')

    def test_clinic_accept_redirects_to_clinic_page(self):
        response = self.client.post(reverse('accept_medical_record', args=[self.appointment.id]))
        self.assertRedirects(response, reverse('clinic_appointments'))

    def test_patient_user_is_denied(self):
        patient_user = self.appointment.patient.user
        self.client.force_login(patient_user)
        response = self.client.post(reverse('accept_medical_record', args=[self.appointment.id]))
        self.assertRedirects(response, reverse('login'), fetch_redirect_response=False)
