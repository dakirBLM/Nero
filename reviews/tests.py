from django.test import TestCase
from django.contrib.auth import get_user_model
from clinics.models import Clinic
from patients.models import Patient
from .models import Review

class ReviewModelTest(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username='testuser', password='testpass', user_type='patient')
        self.patient = Patient.objects.create(user=self.user, full_name='Test Patient', date_of_birth='2000-01-01', gender='M', phone='1234567890')
        self.clinic = Clinic.objects.create(user=User.objects.create_user(username='clinicuser', password='testpass', user_type='clinic'), clinic_name='Test Clinic', tagline='', description='desc', address='addr', city='city', state='state', zip_code='00000', phone_number='123', contact_email='test@clinic.com', specialization='Physical Therapy', established_date='2020-01-01', number_of_therapists=1, languages_spoken='English')

    def test_create_review(self):
        review = Review.objects.create(clinic=self.clinic, patient=self.patient, description='Great!', rating=5)
        self.assertEqual(Review.objects.count(), 1)
        self.assertEqual(review.rating, 5)
