from django.test import TestCase
from django.urls import reverse


class PatientDetailAuthTests(TestCase):
    """patient_detail_view must require authentication. It was missing @login_required,
    and RoleRouteGuard only guards *authenticated* users, so anonymous users reached it."""

    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(reverse('patient_detail', args=[1]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])


from datetime import date

from accounts.forms import ClinicSignUpForm
from accounts.models import User
from clinics.forms import AppointmentForm, ClinicUpdateForm
from clinics.compatibility import clinic_compatibility_errors
from clinics.models import Appointment, Clinic
from patients.forms import MedicalRecordForm
from patients.models import MedicalRecord, Patient

PERMANENT_LABEL = 'Accept patients using a permanent catheter'
INTERMITTENT_LABEL = 'Accept patients using an intermittent catheter'


def _catheter_clinic(username, **overrides):
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


def _catheter_record(suffix, **overrides):
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


class CatheterFormFieldTests(TestCase):
    """Both catheter types must be exposed as separate fields; the generic one is gone."""

    def test_clinic_signup_form_has_both_catheter_fields(self):
        form = ClinicSignUpForm()
        self.assertEqual(form.fields['accepts_permanent_catheter'].label, PERMANENT_LABEL)
        self.assertEqual(form.fields['accepts_intermittent_catheter'].label, INTERMITTENT_LABEL)
        self.assertNotIn('accepts_catheter', form.fields)

    def test_clinic_update_form_has_both_catheter_fields(self):
        form = ClinicUpdateForm()
        self.assertIn('accepts_permanent_catheter', form.fields)
        self.assertIn('accepts_intermittent_catheter', form.fields)
        self.assertNotIn('accepts_catheter', form.fields)

    def test_patient_medical_record_form_has_both_catheter_fields(self):
        form = MedicalRecordForm()
        self.assertIn('uses_permanent_catheter', form.fields)
        self.assertIn('uses_intermittent_catheter', form.fields)

    def test_clinic_update_form_saves_each_type_independently(self):
        clinic = _catheter_clinic('formclinic')
        data = {
            name: ('on' if getattr(clinic, name) else '')
            for name in ClinicUpdateForm.base_fields
            if name.startswith('accepts_')
        }
        data.update({
            'clinic_name': clinic.clinic_name, 'description': 'd', 'address': 'a', 'city': 'c',
            'state': 's', 'zip_code': '1', 'phone_number': '1', 'contact_email': clinic.contact_email,
            'specialization': [Clinic.SPECIALIZATION_CHOICES[0][0]], 'established_date': '2000-01-01',
            'age_range': clinic.age_range, 'languages_spoken': 'English',
            'accepts_permanent_catheter': '',
            'accepts_intermittent_catheter': 'on',
        })
        form = ClinicUpdateForm(data, instance=clinic)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        clinic.refresh_from_db()
        self.assertFalse(clinic.accepts_permanent_catheter)
        self.assertTrue(clinic.accepts_intermittent_catheter)


class CatheterPagesRenderTests(TestCase):
    """The platform pages themselves must show the split, not just the backend."""

    def test_signup_page_shows_two_catheter_checkboxes(self):
        response = self.client.get(reverse('clinic_signup'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="accepts_permanent_catheter"')
        self.assertContains(response, 'name="accepts_intermittent_catheter"')
        self.assertContains(response, PERMANENT_LABEL)
        self.assertContains(response, INTERMITTENT_LABEL)
        self.assertNotContains(response, 'name="accepts_catheter"')
        self.assertNotContains(response, 'Accept patients using a catheter')

    def test_settings_page_shows_two_catheter_toggles(self):
        clinic = _catheter_clinic('settingsclinic')
        self.client.force_login(clinic.user)
        response = self.client.get(reverse('clinic_settings'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="accepts_permanent_catheter"')
        self.assertContains(response, 'name="accepts_intermittent_catheter"')
        self.assertNotContains(response, 'name="accepts_catheter"')

    def _catheter_text(self, url_name, clinic):
        response = self.client.get(reverse(url_name, args=[clinic.id]))
        self.assertEqual(response.status_code, 200)
        marker = 'data-testid="catheter-acceptance">'
        html = response.content.decode()
        self.assertEqual(html.count(marker), 1)
        return html.split(marker, 1)[1].split('</span>', 1)[0]

    def test_public_and_clinic_detail_pages_show_all_four_states(self):
        cases = (
            ('both', True, True, 'Permanent and intermittent'),
            ('permonly', True, False, 'Permanent only'),
            ('intonly', False, True, 'Intermittent only'),
            ('neither', False, False, 'Not accepted'),
        )
        for name, permanent, intermittent, expected in cases:
            clinic = _catheter_clinic(
                name,
                accepts_permanent_catheter=permanent,
                accepts_intermittent_catheter=intermittent,
            )
            with self.subTest(state=name):
                self.assertEqual(self._catheter_text('clinic_detail', clinic), expected)
                self.client.force_login(clinic.user)
                self.assertEqual(self._catheter_text('clinic_datils_clinic', clinic), expected)
                self.client.logout()

    def test_clinic_side_medical_record_shows_specific_type(self):
        clinic = _catheter_clinic('reviewclinic')
        record = _catheter_record('rev', uses_intermittent_catheter=True)
        Appointment.objects.create(
            patient=record.patient, clinic=clinic, medical_record=record,
            appointment_date=date.today(), appointment_time='10:00',
        )
        self.client.force_login(clinic.user)
        response = self.client.get(reverse('see_medical_record_view', args=[record.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            '<span class="label">Uses Permanent Catheter:</span><span class="value">No</span>',
            html=False,
        )
        self.assertContains(
            response,
            '<span class="label">Uses Intermittent Catheter:</span><span class="value">Yes</span>',
            html=False,
        )


class CatheterBookingValidationTests(TestCase):
    def _book(self, record, clinic):
        return AppointmentForm(
            data={
                'medical_record': record.id,
                'appointment_date': date.today(),
                'appointment_time': '10:00',
                'notes': '',
            },
            patient=record.patient,
            clinic=clinic,
        )

    def test_permanent_catheter_patient_rejected_by_clinic_refusing_permanent(self):
        clinic = _catheter_clinic('noperm', accepts_permanent_catheter=False)
        record = _catheter_record('perm', uses_permanent_catheter=True)
        form = self._book(record, clinic)
        self.assertFalse(form.is_valid())
        self.assertIn('Clinic does not accept patients using a permanent catheter.', form.errors['medical_record'])

    def test_intermittent_catheter_patient_rejected_by_clinic_refusing_intermittent(self):
        clinic = _catheter_clinic('noint', accepts_intermittent_catheter=False)
        record = _catheter_record('inter', uses_intermittent_catheter=True)
        form = self._book(record, clinic)
        self.assertFalse(form.is_valid())
        self.assertIn('Clinic does not accept patients using an intermittent catheter.', form.errors['medical_record'])

    def test_clinic_refusing_one_type_still_accepts_the_other(self):
        clinic = _catheter_clinic('onlyint', accepts_permanent_catheter=False)
        record = _catheter_record('okint', uses_intermittent_catheter=True)
        self.assertTrue(self._book(record, clinic).is_valid())
