"""International phone number form field and widget.

Numbers are parsed and validated with libphonenumber (the ``phonenumbers``
package) and stored in E.164 format, e.g. ``+212612345678``.

The widget renders a plain ``<input type="tel">`` that ``static/js/intl-phone.js``
enhances with intl-tel-input: a country flag selector that switches
automatically from the dialling prefix the user types, as-you-type
formatting and per-country validation. The enhanced input posts two
extra hidden fields, ``<name>_full`` (the number in E.164) and
``<name>_country`` (the selected ISO 3166 alpha-2 code). Without
JavaScript the visible input is posted as typed and the server still
validates it, so the client-side layer is a convenience only.
"""

from __future__ import annotations

from typing import NamedTuple

import phonenumbers
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext, gettext_lazy as _

FULL_SUFFIX = '_full'
COUNTRY_SUFFIX = '_country'


class PhoneInputValue(NamedTuple):
    """Raw submission from the widget: the number and the selected region."""

    number: str
    region: str = ''


def parse_phone_number(raw, region=None):
    """Parse ``raw`` into a ``PhoneNumber``, or return ``None`` if impossible.

    ``region`` (ISO 3166 alpha-2) is only used for numbers written without an
    international prefix. A leading ``00`` is treated as ``+``.
    """
    text = (raw or '').strip()
    if not text:
        return None
    if text.startswith('00'):
        text = '+' + text[2:]
    region = (region or '').strip().upper() or None
    try:
        return phonenumbers.parse(text, None if text.startswith('+') else region)
    except phonenumbers.NumberParseException:
        return None


def to_e164(raw, region=None):
    """Return ``raw`` as an E.164 string if it is a valid number, else ``''``."""
    number = parse_phone_number(raw, region)
    if number is None or not phonenumbers.is_valid_number(number):
        return ''
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def region_for_input(raw, region=None):
    """The region a (possibly incomplete) number belongs to, from its +prefix or ``region``."""
    digits = ''.join(ch for ch in (raw or '') if ch.isdigit())
    text = (raw or '').strip()
    if text.startswith('00'):
        digits = digits[2:]
    elif not text.startswith('+'):
        digits = ''
    # Country calling codes are prefix-free and 1-3 digits long.
    for length in (1, 2, 3):
        code = phonenumbers.region_code_for_country_code(int(digits[:length])) if len(digits) >= length else 'ZZ'
        if code != 'ZZ':
            return code
    return (region or '').strip().upper()


def example_number(region):
    """An example mobile number for ``region`` in international format, or ``''``."""
    region = (region or '').strip().upper()
    if len(region) != 2 or region == 'ZZ':  # '001' = non-geographic, 'ZZ' = unknown
        return ''
    number = phonenumbers.example_number_for_type(region, phonenumbers.PhoneNumberType.MOBILE)
    if number is None:
        return ''
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)


class InternationalPhoneInput(forms.TextInput):
    input_type = 'tel'

    def __init__(self, attrs=None):
        base_attrs = {
            'autocomplete': 'tel',
            'inputmode': 'tel',
            'dir': 'ltr',
            'data-intl-phone': '',
        }
        base_attrs.update(attrs or {})
        super().__init__(base_attrs)

    def value_from_datadict(self, data, files, name):
        full = (data.get(name + FULL_SUFFIX) or '').strip()
        typed = (data.get(name) or '').strip()
        region = (data.get(name + COUNTRY_SUFFIX) or '').strip().upper()
        return PhoneInputValue(full or typed, region)

    def value_omitted_from_data(self, data, files, name):
        return name not in data and (name + FULL_SUFFIX) not in data

    def format_value(self, value):
        if isinstance(value, PhoneInputValue):
            value = value.number
        return super().format_value(value)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        widget_attrs = context['widget']['attrs']
        if isinstance(value, PhoneInputValue) and value.region:
            widget_attrs['data-initial-country'] = value.region.lower()
        # Client-side messages, translated into the active language at render time.
        widget_attrs.update({
            'data-msg-detected': gettext('Country: {country} ({code})'),
            'data-msg-invalid': gettext('This phone number is not valid for the selected country.'),
            'data-msg-invalid-country': gettext('Unknown country code. Start with + and your country code.'),
            'data-msg-too-short': gettext('This phone number is too short.'),
            'data-msg-too-long': gettext('This phone number is too long.'),
        })
        return context


class InternationalPhoneField(forms.CharField):
    """A phone number from any country, cleaned to E.164 (``+<country><number>``)."""

    widget = InternationalPhoneInput
    default_error_messages = {
        'invalid': _('Enter a valid phone number including the country code, e.g. +44 7400 123456.'),
        'invalid_example': _('Enter a valid phone number for the selected country, e.g. %(example)s.'),
    }

    def to_python(self, value):
        if isinstance(value, PhoneInputValue):
            raw, region = value
        else:
            raw, region = (value or ''), ''
        raw = str(raw).strip()
        if raw in self.empty_values:
            return self.empty_value

        number = parse_phone_number(raw, region)
        if number is None or not phonenumbers.is_valid_number(number):
            example = example_number(region_for_input(raw, region))
            if example:
                raise ValidationError(
                    self.error_messages['invalid_example'],
                    code='invalid',
                    params={'example': example},
                )
            raise ValidationError(self.error_messages['invalid'], code='invalid')
        return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)
