"""Resolve which clinic an appointment action acts on.

Clinic users always act on their own clinic. The agency dashboard acts on any
clinic by putting ``clinic_id`` in the URL after unlocking the agency session.
"""
from functools import wraps

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse

from agency.auth import is_agency_authenticated

from .models import Clinic


def clinic_or_agency_required(view):
    @wraps(view)
    def wrapper(request, *args, clinic_id=None, **kwargs):
        if clinic_id is not None:
            if not is_agency_authenticated(request):
                return redirect_to_login(request.get_full_path(), reverse('agency_login'))
            clinic = get_object_or_404(Clinic, id=clinic_id)
            request.agency_mode = True
        else:
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if request.user.user_type != 'clinic':
                messages.error(request, 'Access denied.')
                return redirect('login')
            clinic = get_object_or_404(Clinic, user=request.user)
            request.agency_mode = False
        return view(request, clinic, *args, **kwargs)
    return wrapper


def appointments_redirect(request, clinic):
    if getattr(request, 'agency_mode', False):
        return redirect('agency_clinic_appointments', clinic_id=clinic.id)
    return redirect('clinic_appointments')
