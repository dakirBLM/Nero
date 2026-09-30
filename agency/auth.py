"""Password gate for the agency dashboard.

The agency is not a Django user: one shared password (AGENCY_DASHBOARD_PASSWORD)
unlocks the dashboard for the current browser session.
"""
import secrets
from functools import wraps

from django.conf import settings
from django.contrib.auth.views import redirect_to_login
from django.urls import reverse

SESSION_KEY = 'agency_authenticated'


def is_agency_authenticated(request):
    return bool(request.session.get(SESSION_KEY))


def check_agency_password(candidate):
    expected = getattr(settings, 'AGENCY_DASHBOARD_PASSWORD', '') or ''
    if not expected or not candidate:
        return False
    return secrets.compare_digest(candidate.encode('utf-8'), expected.encode('utf-8'))


def unlock_agency(request):
    request.session.cycle_key()
    request.session[SESSION_KEY] = True


def lock_agency(request):
    request.session.pop(SESSION_KEY, None)


def agency_required(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not is_agency_authenticated(request):
            return redirect_to_login(request.get_full_path(), reverse('agency_login'))
        return view(request, *args, **kwargs)
    return wrapper


def login_or_agency_required(view):
    """Like ``login_required`` but an unlocked agency session also passes."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated or is_agency_authenticated(request):
            return view(request, *args, **kwargs)
        return redirect_to_login(request.get_full_path())
    return wrapper
