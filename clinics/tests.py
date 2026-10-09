from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from clinics.models import Clinic


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
