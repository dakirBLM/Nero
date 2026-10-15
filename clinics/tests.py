from datetime import date

from django.test import TestCase
from django.urls import reverse

from accounts.forms import ClinicSignUpForm
from accounts.models import User
from clinics.forms import ClinicUpdateForm
from clinics.models import Clinic, Specialization, Appointment, get_specialization_choices
from patients.models import Patient, MedicalRecord


class PatientDetailAuthTests(TestCase):
    """patient_detail_view must require authentication. It was missing @login_required,
    and RoleRouteGuard only guards *authenticated* users, so anonymous users reached it."""

    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(reverse('patient_detail', args=[1]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])


def _make_user(username, user_type='clinic', password='Testpass123!'):
    return User.objects.create_user(
        username=username,
        email=f'{username}@example.com',
        password=password,
        user_type=user_type,
    )


_CLINIC_DEFAULTS = dict(
    tagline='',
    description=' rehab description',
    address='1 Main St',
    city='Berlin',
    state='Berlin',
    country='Germany',
    continent='Europe',
    zip_code='10115',
    phone_number='+491234567',
    specialization='Convalescence',
    established_date='2020-01-01',
)


def _make_clinic(user, name='Clinic One', contact_email=None, **overrides):
    data = dict(_CLINIC_DEFAULTS)
    data.update(overrides)
    return Clinic.objects.create(
        user=user,
        clinic_name=name,
        contact_email=contact_email or f"{name.replace(' ', '.').lower()}@example.com",
        **data,
    )


def _signup_payload(name='Second Clinic', contact_email='second@example.com'):
    return {
        'clinic_name': name,
        'tagline': '',
        'description': 'second clinic description',
        'address': '2 Main St',
        'city': 'Munich',
        'state': 'Bavaria',
        'country': 'Germany',
        'continent': 'Europe',
        'zip_code': '80331',
        'phone_country_code': '+49',
        'phone_number': '170000000',
        'contact_email': contact_email,
        'website': '',
        'google_maps_url': '',
        'specialization': ['Convalescence'],
        'established_date': '2021-05-01',
        'facilities': '',
        'languages_spoken': 'English',
        'age_range': 'both',
    }


class MultiClinicAccountTests(TestCase):
    """One account (email) can own and manage multiple clinics (many-to-1)."""

    def test_two_clinics_can_share_one_user(self):
        user = _make_user('owner1')
        _make_clinic(user, name='Clinic One')
        _make_clinic(user, name='Clinic Two')
        self.assertEqual(user.clinics.count(), 2)

    def test_single_clinic_login_goes_to_dashboard(self):
        user = _make_user('owner2')
        _make_clinic(user, name='Solo Clinic')
        resp = self.client.post(
            reverse('login'),
            {'identifier': 'owner2', 'password': 'Testpass123!'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/clinics/dashboard/')

    def test_multi_clinic_login_goes_to_select(self):
        user = _make_user('owner3')
        _make_clinic(user, name='Clinic A')
        _make_clinic(user, name='Clinic B')
        resp = self.client.post(
            reverse('login'),
            {'identifier': 'owner3', 'password': 'Testpass123!'},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('clinic_select'))

    def test_dashboard_without_selection_redirects_to_select(self):
        user = _make_user('owner4')
        _make_clinic(user, name='Clinic A')
        _make_clinic(user, name='Clinic B')
        self.client.force_login(user)
        resp = self.client.get(reverse('clinic_dashboard'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('clinic_select'))

    def test_select_page_lists_only_owned_clinics(self):
        owner = _make_user('owner5')
        other = _make_user('stranger')
        mine = _make_clinic(owner, name='Mine One')
        mine_two = _make_clinic(owner, name='Mine Two')
        foreign = _make_clinic(other, name='Not Mine')
        self.client.force_login(owner)
        resp = self.client.get(reverse('clinic_select'))
        self.assertEqual(resp.status_code, 200)
        content = resp.content.decode()
        self.assertIn('Mine One', content)
        self.assertIn('Mine Two', content)
        self.assertNotIn('Not Mine', content)
        self.assertNotIn(f'name="clinic_id" value="{foreign.id}"', content)
        self.assertIn(f'name="clinic_id" value="{mine.id}"', content)
        self.assertIn(f'name="clinic_id" value="{mine_two.id}"', content)

    def test_switch_to_own_clinic_scopes_views(self):
        user = _make_user('owner6')
        first = _make_clinic(user, name='First Clinic')
        second = _make_clinic(user, name='Second Clinic')
        self.client.force_login(user)
        resp = self.client.post(reverse('clinic_select'), {'clinic_id': second.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('clinic_dashboard'))
        self.assertEqual(self.client.session.get('active_clinic_id'), second.id)
        # Dashboard and settings now act on the selected clinic.
        resp = self.client.get(reverse('clinic_dashboard'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['clinic'].id, second.id)
        resp = self.client.get(reverse('clinic_settings'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['clinic'].id, second.id)
        self.assertNotEqual(first.id, second.id)

    def test_switch_to_foreign_clinic_is_rejected(self):
        owner = _make_user('owner7')
        other = _make_user('rival')
        _make_clinic(owner, name='My Clinic')
        _make_clinic(owner, name='My Second Clinic')
        foreign = _make_clinic(other, name='Rival Clinic')
        self.client.force_login(owner)
        resp = self.client.post(reverse('clinic_select'), {'clinic_id': foreign.id})
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('clinic_select'))
        self.assertIsNone(self.client.session.get('active_clinic_id'))

    def test_single_clinic_select_shortcuts_to_dashboard(self):
        user = _make_user('owner8')
        _make_clinic(user, name='Solo')
        self.client.force_login(user)
        resp = self.client.get(reverse('clinic_select'))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('clinic_dashboard'))

    def test_add_second_clinic_via_signup_same_account(self):
        user = _make_user('owner9')
        _make_clinic(user, name='First Clinic', contact_email='first@example.com')
        self.client.force_login(user)
        resp = self.client.post(
            reverse('clinic_signup'), _signup_payload(), follow=False
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('clinic_dashboard'))
        self.assertEqual(Clinic.objects.filter(user=user).count(), 2)
        self.assertEqual(User.objects.filter(email='owner9@example.com').count(), 1)
        # New clinic becomes the active one.
        active_id = self.client.session.get('active_clinic_id')
        self.assertEqual(
            Clinic.objects.get(id=active_id).clinic_name, 'Second Clinic'
        )

    def test_contact_email_unique_across_different_owners(self):
        owner = _make_user('owner10')
        _make_clinic(owner, name='Mine', contact_email='shared@example.com')
        self.client.force_login(owner)
        payload = _signup_payload(name='Dup', contact_email='shared@example.com')
        resp = self.client.post(reverse('clinic_signup'), payload)
        # Same owner reusing their own contact email is allowed.
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(Clinic.objects.filter(user=owner).count(), 2)

        rival = _make_user('rival10')
        self.client.force_login(rival)
        payload = _signup_payload(name='Rival Dup', contact_email='shared@example.com')
        resp = self.client.post(reverse('clinic_signup'), payload)
        self.assertEqual(resp.status_code, 200)  # form re-rendered with error
        self.assertEqual(Clinic.objects.filter(user=rival).count(), 0)


def _make_staff():
    return User.objects.create_superuser(
        username='specboss', email='specboss@example.com', password='Testpass123!'
    )


def _make_patient_user(username):
    user = _make_user(username, user_type='patient')
    Patient.objects.create(user=user, full_name=username.title(), gender='M', phone='1')
    return user


class DynamicSpecializationTests(TestCase):
    """Specializations are admin-managed rows, not hardcoded choices."""

    def test_default_four_are_seeded(self):
        self.assertEqual(
            set(Specialization.objects.values_list('name', flat=True)),
            {'Convalescence', 'Weight loss', 'Musculoskeletal treatment', 'Neurological treatment'},
        )

    def test_admin_add_appears_in_signup_choices(self):
        self.client.force_login(_make_staff())
        resp = self.client.post(
            reverse('admin:clinics_specialization_add'), {'name': 'Cardiac Rehabilitation'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertTrue(Specialization.objects.filter(name='Cardiac Rehabilitation').exists())
        choices = dict(ClinicSignUpForm().fields['specialization'].choices)
        self.assertIn('Cardiac Rehabilitation', choices)
        self.assertIn('Convalescence', choices)

    def test_admin_delete_blocked_when_in_use(self):
        owner = _make_user('specowner')
        _make_clinic(owner, name='Heart Clinic', specialization='Convalescence')
        spec = Specialization.objects.get(name='Convalescence')
        self.client.force_login(_make_staff())
        resp = self.client.post(
            reverse('admin:clinics_specialization_delete', args=[spec.pk]), {'post': 'yes'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], reverse('admin:clinics_specialization_changelist'))
        self.assertTrue(Specialization.objects.filter(name='Convalescence').exists())

    def test_admin_delete_allowed_when_unused(self):
        spec = Specialization.objects.create(name='Temporary Type')
        self.client.force_login(_make_staff())
        resp = self.client.post(
            reverse('admin:clinics_specialization_delete', args=[spec.pk]), {'post': 'yes'}
        )
        self.assertEqual(resp.status_code, 302)
        self.assertFalse(Specialization.objects.filter(name='Temporary Type').exists())

    def test_settings_form_keeps_legacy_value(self):
        owner = _make_user('legacyowner')
        clinic = _make_clinic(owner, name='Legacy Clinic', specialization='Legacy Care, Convalescence')
        form = ClinicUpdateForm(instance=clinic)
        self.assertIn('Legacy Care', dict(form.fields['specialization'].choices))
        self.assertEqual(
            sorted(form.fields['specialization'].initial), ['Convalescence', 'Legacy Care']
        )
        # Submitting the legacy value back validates fine (no silent drop).
        bound = ClinicUpdateForm(
            data={'specialization': ['Legacy Care', 'Convalescence']}, instance=clinic
        )
        self.assertNotIn('specialization', bound.errors)
        self.assertEqual(
            sorted(bound.cleaned_data['specialization']), ['Convalescence', 'Legacy Care']
        )

    def test_patient_search_filter_with_new_type(self):
        user = _make_user('searchpatient', user_type='patient')
        Patient.objects.create(user=user, full_name='Searcher', gender='M', phone='1')
        owner = _make_user('heartowner')
        _make_clinic(owner, name='Heart Clinic', specialization='Cardiac Rehabilitation')
        Specialization.objects.create(name='Cardiac Rehabilitation')
        self.client.force_login(user)
        resp = self.client.get(reverse('search_clinics'), {'specialization': 'Cardiac Rehabilitation'})
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Heart Clinic')

    def test_recommendation_filter_lists_new_type(self):
        from recommendations.views import _base_filter_context

        user = _make_patient_user('recpatient')
        Specialization.objects.create(name='Cardiac Rehabilitation')
        context = _base_filter_context(user.patient)
        self.assertIn('Cardiac Rehabilitation', context['clinic_types'])
        self.assertIn('Convalescence', context['clinic_types'])


class ClinicWaitingBoxTests(TestCase):
    """The 'waiting for patient booking details' box must only render while
    the patient still owes details (pending), not after they submitted."""

    def _appointment(self, username, status, **overrides):
        user = _make_user(username)
        clinic = _make_clinic(user, name=f'{username} clinic')
        patient_user = _make_user(f'{username}-patient', user_type='patient')
        patient = Patient.objects.create(
            user=patient_user, full_name=f'{username} patient', gender='M', phone='1'
        )
        record = MedicalRecord.objects.create(
            patient=patient, first_name='A', last_name='B', gender='M',
            date_of_birth=date(1990, 1, 1), address='a', country='C',
            height=170, weight=70, main_diagnosis='dx', injury_date=date(2020, 1, 1),
            movement_ability='independent',
        )
        appointment = Appointment.objects.create(
            patient=patient, clinic=clinic, medical_record=record,
            status=status, **overrides,
        )
        return user, appointment

    def _page(self, user):
        self.client.force_login(user)
        return self.client.get(reverse('clinic_appointments'))

    def test_waiting_box_shown_while_pending(self):
        user, _ = self._appointment('waiter', 'pending', medical_record_accepted=True)
        resp = self._page(user)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Waiting for patient to submit booking details')

    def test_waiting_box_hidden_after_no_accommodation_submit(self):
        # The exact reported case: submitted with no accommodation (dates stay
        # None by design) yet the stale box kept rendering.
        user, _ = self._appointment(
            'submitted', 'accepted_record_accepted_accommodation',
            medical_record_accepted=True, accommodation_type='no_accommodation',
            needs_accommodation=False,
        )
        resp = self._page(user)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'Waiting for patient to submit booking details')
        self.assertNotContains(resp, 'Awaiting patient response')


class RejectModalTests(TestCase):
    """Reject-medical uses a styled in-page modal (no native confirm()),
    requires a reason first, and the form still rejects properly."""

    def _pending(self, username):
        user = _make_user(username)
        clinic = _make_clinic(user, name=f'{username} clinic')
        patient_user = _make_user(f'{username}-patient', user_type='patient')
        patient = Patient.objects.create(
            user=patient_user, full_name=f'{username} patient', gender='M', phone='1'
        )
        record = MedicalRecord.objects.create(
            patient=patient, first_name='A', last_name='B', gender='M',
            date_of_birth=date(1990, 1, 1), address='a', country='C',
            height=170, weight=70, main_diagnosis='dx', injury_date=date(2020, 1, 1),
            movement_ability='independent',
        )
        appointment = Appointment.objects.create(
            patient=patient, clinic=clinic, medical_record=record, status='pending',
        )
        return user, appointment

    def test_no_native_confirm_and_modal_present(self):
        user, appointment = self._pending('rejector')
        self.client.force_login(user)
        resp = self.client.get(reverse('clinic_appointments'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "confirm('Reject this medical request?')")
        self.assertContains(resp, f'reject-modal-{appointment.id}')
        self.assertContains(resp, f'reject-form-{appointment.id}')
        self.assertContains(resp, 'openRejectModal')

    def test_reject_with_reason_still_works(self):
        user, appointment = self._pending('rejector2')
        self.client.force_login(user)
        resp = self.client.post(
            reverse('reject_medical_record', args=[appointment.id]),
            {'medical_rejection_reason': 'capacity_unavailable'},
        )
        self.assertEqual(resp.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'rejected_medical_record')
        self.assertEqual(appointment.medical_rejection_reason, 'capacity_unavailable')


class ClinicActionModalTests(TestCase):
    """Reject-booking / mark-upcoming / status-change use the shared styled
    in-page modal, never native confirm(); the POSTs still work."""

    def _setup(self, username, status='pending', **overrides):
        user = _make_user(username)
        clinic = _make_clinic(user, name=f'{username} clinic')
        patient_user = _make_user(f'{username}-patient', user_type='patient')
        patient = Patient.objects.create(
            user=patient_user, full_name=f'{username} patient', gender='M', phone='1'
        )
        record = MedicalRecord.objects.create(
            patient=patient, first_name='A', last_name='B', gender='M',
            date_of_birth=date(1990, 1, 1), address='a', country='C',
            height=170, weight=70, main_diagnosis='dx', injury_date=date(2020, 1, 1),
            movement_ability='independent',
        )
        appointment = Appointment.objects.create(
            patient=patient, clinic=clinic, medical_record=record,
            status=status, **overrides,
        )
        self.client.force_login(user)
        return appointment

    def test_no_native_confirms_and_modal_present(self):
        self._setup('modaluser')
        resp = self.client.get(reverse('clinic_appointments'))
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "confirm('")
        self.assertContains(resp, 'action-modal')
        self.assertContains(resp, 'openActionModal')

    def test_mark_upcoming_post_still_works(self):
        appointment = self._setup('upcominguser', status='paid')
        resp = self.client.post(reverse('mark_appointment_upcoming', args=[appointment.id]))
        self.assertEqual(resp.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'upcoming')

    def _setup_with_dates(self, username):
        # Renders the propose/reject block: pending + medical accepted +
        # patient dates submitted (otherwise the waiting box shows instead).
        return self._setup(
            username, status='pending', medical_record_accepted=True,
            treatment_start_date=date(2026, 10, 20), treatment_end_date=date(2026, 10, 25),
            accommodation_type='single_room', needs_accommodation=True,
        )

    def test_no_nested_forms_and_reject_action_correct(self):
        from html.parser import HTMLParser

        appointment = self._setup_with_dates('nesteduser')

        class FormDepth(HTMLParser):
            def __init__(self):
                super().__init__()
                self.depth = 0
                self.max_depth = 0
                self.reject_actions = []

            def handle_starttag(self, tag, attrs):
                if tag == 'form':
                    self.depth += 1
                    self.max_depth = max(self.max_depth, self.depth)
                    form_id = dict(attrs).get('id', '')
                    if form_id.startswith('reject-booking-form-'):
                        self.reject_actions.append(dict(attrs).get('action', ''))

            def handle_endtag(self, tag):
                if tag == 'form':
                    self.depth -= 1

        resp = self.client.get(reverse('clinic_appointments'))
        self.assertEqual(resp.status_code, 200)
        parser = FormDepth()
        parser.feed(resp.content.decode())
        self.assertLessEqual(parser.max_depth, 1)
        self.assertEqual(len(parser.reject_actions), 1)
        self.assertIn('facility-reject-booking', parser.reject_actions[0])
        self.assertIn(str(appointment.id), parser.reject_actions[0])

    def test_propose_post_still_works(self):
        appointment = self._setup_with_dates('proposer')
        resp = self.client.post(
            reverse('facility_propose_dates', args=[appointment.id]),
            {
                'proposed_start_date': '2027-01-10',
                'proposed_end_date': '2027-01-15',
                'clinic_proposal_note': 'Different dates please.',
            },
        )
        self.assertEqual(resp.status_code, 302)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, 'accepted_record_accommodation_change_requested')
