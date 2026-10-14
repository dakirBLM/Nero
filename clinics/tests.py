from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts.forms import ClinicSignUpForm
from accounts.models import User
from clinics.forms import ClinicUpdateForm
from clinics.models import Clinic, Specialization, get_specialization_choices
from patients.models import Patient
from clinics.models import Clinic
from core.validators import validate_established_year


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
    established_year=2020,
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
        'phone_number': '+49 170 1234567',
        'contact_email': contact_email,
        'website': '',
        'google_maps_url': '',
        'specialization': ['Convalescence'],
        'established_year': 2021,
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
class EstablishedYearTests(TestCase):
    """Clinics store an establishment *year* (int), validated to 1000..today."""

    def test_validator_accepts_reasonable_year(self):
        validate_established_year(1000)
        validate_established_year(1750)
        validate_established_year(2000)
        validate_established_year(date.today().year)

    def test_validator_rejects_out_of_range(self):
        for bad in (999, 0, -5, date.today().year + 1, date.today().year + 50):
            with self.subTest(year=bad):
                with self.assertRaises(ValidationError):
                    validate_established_year(bad)

    def test_validator_rejects_non_integers(self):
        for bad in ('2015', 2015.0, None, True):
            with self.subTest(year=bad):
                with self.assertRaises(ValidationError):
                    validate_established_year(bad)

    def test_years_in_operation_derives_from_year(self):
        user = _make_user('yearowner')
        clinic = _make_clinic(user, name='Old Clinic', established_year=2000)
        self.assertEqual(clinic.years_in_operation, date.today().year - 2000)

    def test_signup_rejects_bad_year(self):
        user = _make_user('yearowner2')
        _make_clinic(user, name='First', contact_email='y1@example.com')
        self.client.force_login(user)
        for bad in (999, date.today().year + 1):
            with self.subTest(year=bad):
                payload = _signup_payload(
                    name=f'Bad {bad}', contact_email=f'bad{bad}@example.com'
                )
                payload['established_year'] = bad
                resp = self.client.post(reverse('clinic_signup'), payload)
                self.assertEqual(resp.status_code, 200)  # re-rendered with error
        self.assertEqual(Clinic.objects.filter(user=user).count(), 1)

    def test_signup_accepts_year(self):
        user = _make_user('yearowner3')
        _make_clinic(user, name='First', contact_email='y3@example.com')
        self.client.force_login(user)
        payload = _signup_payload(name='Year Clinic', contact_email='yc@example.com')
        payload['established_year'] = 2015
        resp = self.client.post(reverse('clinic_signup'), payload)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(
            Clinic.objects.get(user=user, clinic_name='Year Clinic').established_year,
            2015,
        )
