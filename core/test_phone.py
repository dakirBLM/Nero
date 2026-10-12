from django import forms
from django.http import QueryDict
from django.test import SimpleTestCase, TestCase

from accounts.forms import PatientSignUpForm
from core.phone import InternationalPhoneField, PhoneInputValue, to_e164
from patients.models import Patient


class PhoneForm(forms.Form):
    phone = InternationalPhoneField()
    optional_phone = InternationalPhoneField(required=False)


def phone_form(**data):
    query = QueryDict(mutable=True)
    query.update(data)
    return PhoneForm(query)


class InternationalPhoneFieldTests(SimpleTestCase):
    def test_international_numbers_from_any_country_are_cleaned_to_e164(self):
        cases = {
            '+212 6 12 34 56 78': '+212612345678',   # Morocco
            '+44 7400 123456': '+447400123456',      # United Kingdom
            '+1 (201) 555-0123': '+12015550123',     # United States
            '+33 6 12 34 56 78': '+33612345678',     # France
            '+971 50 123 4567': '+971501234567',     # United Arab Emirates
            '0049 1512 3456789': '+4915123456789',   # Germany, 00 prefix
        }
        for typed, expected in cases.items():
            with self.subTest(typed=typed):
                form = phone_form(phone=typed)
                self.assertTrue(form.is_valid(), form.errors)
                self.assertEqual(form.cleaned_data['phone'], expected)

    def test_national_number_uses_the_selected_country(self):
        form = phone_form(phone='06 12 34 56 78', phone_country='ma')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['phone'], '+212612345678')

    def test_number_detected_by_the_browser_is_preferred(self):
        form = phone_form(phone='+44 7400 123456', phone_full='+447400123456', phone_country='gb')
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['phone'], '+447400123456')

    def test_national_number_without_country_is_rejected(self):
        form = phone_form(phone='0612345678')
        self.assertFalse(form.is_valid())
        self.assertIn('country code', form.errors['phone'][0])

    def test_invalid_number_for_country_is_rejected_with_an_example(self):
        form = phone_form(phone='+212 12')
        self.assertFalse(form.is_valid())
        self.assertIn('+212', form.errors['phone'][0])

    def test_garbage_is_rejected(self):
        form = phone_form(phone='not a phone')
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)

    def test_required_and_optional(self):
        form = phone_form(phone='', optional_phone='')
        self.assertFalse(form.is_valid())
        self.assertIn('phone', form.errors)
        self.assertNotIn('optional_phone', form.errors)
        self.assertEqual(form.cleaned_data['optional_phone'], '')

    def test_widget_renders_enhanceable_tel_input(self):
        html = str(PhoneForm(initial={'phone': '+212612345678'})['phone'])
        self.assertIn('type="tel"', html)
        self.assertIn('data-intl-phone', html)
        self.assertIn('autocomplete="tel"', html)
        self.assertIn('value="+212612345678"', html)

    def test_invalid_submission_is_redisplayed_with_its_country(self):
        form = phone_form(phone='06 12', phone_country='ma')
        self.assertFalse(form.is_valid())
        html = str(form['phone'])
        self.assertIn('value="06 12"', html)
        self.assertIn('data-initial-country="ma"', html)

    def test_to_e164(self):
        self.assertEqual(to_e164('+212 6 12 34 56 78'), '+212612345678')
        self.assertEqual(to_e164('0000000000'), '')
        self.assertEqual(to_e164(''), '')
        self.assertEqual(to_e164(None), '')

    def test_plain_string_values_are_accepted(self):
        field = InternationalPhoneField()
        self.assertEqual(field.clean('+447400123456'), '+447400123456')
        self.assertEqual(field.clean(PhoneInputValue('07400 123456', 'GB')), '+447400123456')


class PatientSignUpPhoneTests(TestCase):
    def signup_data(self, **overrides):
        data = {
            'username': 'phone-patient',
            'email': 'phone-patient@example.com',
            'full_name': 'Phone Patient',
            'date_of_birth': '1990-01-01',
            'gender': 'F',
            'phone_number': '+212 6 12 34 56 78',
            'password1': 'S3cure-passw0rd!',
            'password2': 'S3cure-passw0rd!',
        }
        data.update(overrides)
        return data

    def test_signup_stores_phone_in_e164(self):
        form = PatientSignUpForm(self.signup_data())
        self.assertTrue(form.is_valid(), form.errors)
        user = form.save()
        self.assertEqual(Patient.objects.get(user=user).phone, '+212612345678')

    def test_signup_rejects_invalid_phone(self):
        form = PatientSignUpForm(self.signup_data(phone_number='+212 12'))
        self.assertFalse(form.is_valid())
        self.assertIn('phone_number', form.errors)
