from django.test import TestCase
from django.urls import reverse


class PatientDetailAuthTests(TestCase):
    """patient_detail_view must require authentication. It was missing @login_required,
    and RoleRouteGuard only guards *authenticated* users, so anonymous users reached it."""

    def test_anonymous_is_redirected_to_login(self):
        resp = self.client.get(reverse('patient_detail', args=[1]))
        self.assertEqual(resp.status_code, 302)
        self.assertIn('/accounts/login/', resp['Location'])
