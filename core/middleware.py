from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import redirect
from django.utils import timezone


class SessionUserIntegrityMiddleware:
    """Force logout when the session points to a deleted user account."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_path = getattr(settings, 'LOGIN_URL', '/accounts/login/')

    def __call__(self, request):
        auth_user_id = request.session.get('_auth_user_id')
        user_missing = False
        if auth_user_id:
            User = get_user_model()
            user_missing = not User.objects.filter(pk=auth_user_id).exists()

        # Stale session detected: session references a deleted user account.
        if auth_user_id and user_missing:
            request.session.flush()
            if request.path != self.login_path:
                messages.warning(request, 'Your account is no longer available. Please log in again.')
                return redirect('login')

        return self.get_response(request)


class RoleRouteGuardMiddleware:
    """Protect role-specific routes from cross-role access."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, 'user', None)
        if user and user.is_authenticated:
            path = request.path
            user_type = getattr(user, 'user_type', None)

            clinic_allowed_patient_paths = (
                path.startswith('/patients/see-medical-record')
                or path.startswith('/patients/medical-record/') and (
                    '/download-report/' in path or '/view-video/' in path
                )
                or path.startswith('/patients/secure-media/')
                or path.startswith('/patients/search-all/')
                or path.startswith('/patients/search-for-clinic/')
            )

            if path.startswith('/patients/') and path != '/patients/signup/':
                if user_type != 'patient' and not (user_type == 'clinic' and clinic_allowed_patient_paths):
                    messages.error(request, 'Access denied.')
                    return redirect('login')

            clinic_private_prefixes = (
                '/clinics/dashboard/',
                '/clinics/settings/',
                '/clinics/manage-gallery/',
                '/clinics/delete-gallery-image/',
                '/clinics/service/',
                '/clinics/assign-patient/',
                '/clinics/clinic-appointments/',
                '/clinics/appointment/',
                '/clinics/patient/',
                '/clinics/my-posts/',
            )

            if path.startswith(clinic_private_prefixes):
                if user_type != 'clinic':
                    messages.error(request, 'Access denied.')
                    return redirect('login')

        return self.get_response(request)


class LastSeenMiddleware:
    """Middleware to update authenticated patient's `last_seen` timestamp."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        try:
            user = getattr(request, 'user', None)
            if user and user.is_authenticated:
                if hasattr(user, 'patient'):
                    try:
                        user.patient.last_seen = timezone.now()
                        user.patient.save(update_fields=['last_seen'])
                    except Exception:
                        pass
                if hasattr(user, 'clinic'):
                    try:
                        user.clinic.last_seen = timezone.now()
                        user.clinic.save(update_fields=['last_seen'])
                    except Exception:
                        pass
        except Exception:
            # don't let presence update break requests
            pass
        return response
