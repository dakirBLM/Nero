"""Shared country choices used across signup and medical forms.

Phone numbers are handled by :mod:`core.phone`.
"""

from __future__ import annotations


def _build_country_choices():
    try:
        import pycountry  # type: ignore

        countries = sorted(
            {
                country.name
                for country in pycountry.countries
                if getattr(country, 'name', '').strip()
            }
        )
    except Exception:
        countries = [
            'Afghanistan', 'Albania', 'Algeria', 'Argentina', 'Australia', 'Austria', 'Bahrain',
            'Bangladesh', 'Belgium', 'Brazil', 'Bulgaria', 'Canada', 'Chile', 'China', 'Colombia',
            'Croatia', 'Cyprus', 'Czech Republic', 'Denmark', 'Egypt', 'Finland', 'France', 'Germany',
            'Greece', 'Hungary', 'Iceland', 'India', 'Indonesia', 'Iran', 'Iraq', 'Ireland', 'Israel',
            'Italy', 'Japan', 'Jordan', 'Kenya', 'Kuwait', 'Lebanon', 'Libya', 'Malaysia', 'Mexico',
            'Morocco', 'Netherlands', 'New Zealand', 'Nigeria', 'Norway', 'Oman', 'Pakistan', 'Peru',
            'Philippines', 'Poland', 'Portugal', 'Qatar', 'Romania', 'Saudi Arabia', 'Singapore',
            'South Africa', 'South Korea', 'Spain', 'Sweden', 'Switzerland', 'Syria', 'Tunisia',
            'Turkey', 'Ukraine', 'United Arab Emirates', 'United Kingdom', 'United States', 'Venezuela',
        ]

    return [('', 'Select country')] + [(country, country) for country in countries]


COUNTRY_CHOICES = _build_country_choices()
