from django.test import TestCase
from django.urls import reverse


class HealthEndpointTests(TestCase):
    def test_healthz_ok(self):
        resp = self.client.get(reverse('healthz'))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.content, b'ok')

    def test_readyz_ok(self):
        resp = self.client.get(reverse('readyz'))
        self.assertEqual(resp.status_code, 200)
        self.assertJSONEqual(resp.content, {'status': 'ready'})
