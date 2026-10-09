"""Active-clinic resolution for accounts that may own multiple clinics.

A single account (``User`` with ``user_type == 'clinic'``) can own one or
more ``Clinic`` rows. Every clinic-scoped view must act on exactly one
clinic — the *active* clinic:

* single-clinic accounts resolve directly (previous behavior, unchanged);
* multi-clinic accounts resolve from ``request.session['active_clinic_id']``;
* when no clinic can be resolved the caller redirects (selection page when
  the account owns several clinics, signup page when it owns none).

All ownership checks live here so no view ever trusts a client-supplied id.
"""
from django.contrib import messages
from django.shortcuts import redirect

SESSION_KEY = 'active_clinic_id'


def owned_clinics(user):
    """Queryset of clinics owned by ``user``, oldest first."""
    from .models import Clinic
    return Clinic.objects.filter(user=user).order_by('id')


def user_has_clinic(user):
    """True when ``user`` is an authenticated account owning >= 1 clinic."""
    return (
        bool(getattr(user, 'is_authenticated', False))
        and getattr(user, 'user_type', None) == 'clinic'
        and owned_clinics(user).exists()
    )


def get_active_clinic(request):
    """Return the clinic this request acts on, or None when unavailable."""
    user = getattr(request, 'user', None)
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    if getattr(user, 'user_type', None) != 'clinic':
        return None
    clinics = list(owned_clinics(user))
    if not clinics:
        return None
    if len(clinics) == 1:
        return clinics[0]
    try:
        selected_id = int(request.session.get(SESSION_KEY))
    except (TypeError, ValueError):
        return None
    for clinic in clinics:
        if clinic.id == selected_id:
            return clinic
    return None


def set_active_clinic(request, clinic):
    """Remember ``clinic`` as the active one for this session."""
    request.session[SESSION_KEY] = clinic.id


def clear_active_clinic(request):
    request.session.pop(SESSION_KEY, None)


def latest_seen_clinic(user):
    """Most recently seen clinic of ``user`` (for online-status display)."""
    from .models import Clinic
    qs = Clinic.objects.filter(user=user)
    seen = qs.exclude(last_seen__isnull=True).order_by('-last_seen').first()
    return seen if seen is not None else qs.first()


def contact_is_online(other, minutes=5):
    """True when ``other`` (patient or clinic account) was seen recently."""
    from datetime import timedelta

    from django.utils import timezone

    try:
        patient = getattr(other, 'patient', None)
    except Exception:
        patient = None
    if patient is not None and getattr(patient, 'last_seen', None):
        try:
            if timezone.now() - patient.last_seen <= timedelta(minutes=minutes):
                return True
        except Exception:
            pass
    try:
        clinic = latest_seen_clinic(other)
    except Exception:
        clinic = None
    if clinic is not None and getattr(clinic, 'last_seen', None):
        try:
            if timezone.now() - clinic.last_seen <= timedelta(minutes=minutes):
                return True
        except Exception:
            pass
    return False


def active_clinic_or_redirect(request):
    """Return ``(clinic, None)``, or ``(None, redirect_response)``.

    Use at the top of clinic-scoped views::

        clinic, _redirect = active_clinic_or_redirect(request)
        if _redirect is not None:
            return _redirect
    """
    clinic = get_active_clinic(request)
    if clinic is not None:
        return clinic, None
    user = getattr(request, 'user', None)
    if user_has_clinic(user):
        return None, redirect('clinic_select')
    messages.info(request, 'Please complete your clinic profile to continue.')
    return None, redirect('clinic_signup')
