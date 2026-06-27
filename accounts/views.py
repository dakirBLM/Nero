from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.contrib.sites.models import Site
from django.urls import reverse


def _sync_user_type_from_profile(user):
    """Keep user_type aligned with the concrete profile attached to the user."""
    has_patient_profile = False
    has_clinic_profile = False

    try:
        from patients.models import Patient
        has_patient_profile = Patient.objects.filter(user=user).exists()
    except Exception:
        has_patient_profile = False

    try:
        from clinics.models import Clinic
        has_clinic_profile = Clinic.objects.filter(user=user).exists()
    except Exception:
        has_clinic_profile = False

    # If only one profile exists, trust that profile as source of truth.
    if has_clinic_profile and not has_patient_profile and user.user_type != 'clinic':
        user.user_type = 'clinic'
        user.save(update_fields=['user_type'])
    elif has_patient_profile and not has_clinic_profile and user.user_type != 'patient':
        user.user_type = 'patient'
        user.save(update_fields=['user_type'])

    return has_patient_profile, has_clinic_profile

def _get_google_login_url(request):
    """Return the Google login URL when Google OAuth is configured either via
    settings (GOOGLE_CLIENT_ID/GOOGLE_CLIENT_SECRET env vars) OR via a DB SocialApp."""
    try:
        # 1) Settings-based config (12-factor: env vars build the provider APP).
        providers = getattr(settings, 'SOCIALACCOUNT_PROVIDERS', {}) or {}
        google_app = (providers.get('google', {}) or {}).get('APP', {}) or {}
        if google_app.get('client_id'):
            return '/accounts/social/google/login/'

        # 2) Fallback: a Google SocialApp row linked to the current site (admin).
        from allauth.socialaccount.models import SocialApp

        site_obj = None
        site_id = getattr(settings, 'SITE_ID', None)
        if site_id:
            site_obj = Site.objects.filter(id=site_id).first()
        if site_obj is None:
            site_obj = Site.objects.filter(domain=request.get_host()).first()
        if site_obj is None:
            return None

        if SocialApp.objects.filter(provider='google', sites=site_obj).exists():
            return '/accounts/social/google/login/'
        return None
    except Exception:
        return None

class CustomLoginView(LoginView):
    template_name = 'accounts/login.html'

    def post(self, request, *args, **kwargs):
        identifier = (request.POST.get('identifier') or '').strip()
        password = request.POST.get('password') or ''
        remember = request.POST.get('remember') == 'on'

        if not identifier or not password:
            messages.error(request, 'Please enter your username/email and password.')
            return redirect('login')

        User = get_user_model()
        matched_user = (
            User.objects.filter(username__iexact=identifier).first()
            or User.objects.filter(email__iexact=identifier).first()
        )

        if matched_user is None:
            messages.error(request, 'No user found with this username or email.')
            return redirect('login')

        user = authenticate(request, username=matched_user.username, password=password)

        if user is None:
            messages.error(request, 'The email/username or password is wrong.')
            return redirect('login')

        login(request, user)
        request.session.set_expiry(7200 if remember else 0)
        return redirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        try:
            context = super().get_context_data(**kwargs)
        except Site.DoesNotExist:
            # Fallback when SITE_ID points to a missing Site row.
            context = {
                'form': self.get_form(),
                self.redirect_field_name: self.get_redirect_url(),
                'site': None,
                'site_name': self.request.get_host(),
            }
            if self.extra_context:
                context.update(self.extra_context)

        context.update(kwargs)
        context['google_login_url'] = _get_google_login_url(self.request)
        if context['google_login_url']:
            context['google_patient_start_url'] = reverse('google_start', kwargs={'role': 'patient'})
            context['google_clinic_start_url'] = reverse('google_start', kwargs={'role': 'clinic'})
        else:
            context['google_patient_start_url'] = None
            context['google_clinic_start_url'] = None
        return context
    
    def get(self, request, *args, **kwargs):
        # Check for Google role conflict and display error
        if request.session.get('google_role_conflict'):
            request.session.pop('google_role_conflict', None)
            existing_role = request.session.pop('existing_role', 'unknown')
            attempted_role = request.session.pop('attempted_role', 'unknown')
            
            user_type_display = 'Patient' if existing_role == 'patient' else 'Clinic' if existing_role == 'clinic' else existing_role
            attempted_display = 'Patient' if attempted_role == 'patient' else 'Clinic' if attempted_role == 'clinic' else attempted_role
            
            messages.error(
                request,
                f'This Google account is already connected to a {user_type_display} account. '
                f'You cannot use it to sign up as a {attempted_display}. '
                f'Please use a different Google account or contact support.'
            )
        
        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        user = self.request.user
        has_patient_profile, has_clinic_profile = _sync_user_type_from_profile(user)
        
        # Check for Google role conflict
        if self.request.session.get('google_role_conflict'):
            self.request.session.pop('google_role_conflict', None)
            existing_role = self.request.session.pop('existing_role', 'unknown')
            attempted_role = self.request.session.pop('attempted_role', 'unknown')
            
            user_type_display = 'Patient' if existing_role == 'patient' else 'Clinic' if existing_role == 'clinic' else existing_role
            attempted_display = 'Patient' if attempted_role == 'patient' else 'Clinic' if attempted_role == 'clinic' else attempted_role
            
            messages.error(
                self.request,
                f'This Google account is already connected to a {user_type_display} account. '
                f'You cannot use it to sign up as a {attempted_display}. '
                f'Please use a different Google account or contact support.'
            )
            return redirect('login')
        
        # Route to appropriate dashboard based on user_type
        if user.user_type == 'patient':
            return '/patients/dashboard/'
        elif user.user_type == 'clinic':
            if not has_clinic_profile:
                messages.info(self.request, 'Please complete your clinic profile to finish registration.')
                return '/clinics/signup/?from_google=1'
            return '/clinics/dashboard/'
        # Fallback to concrete profile if user_type is empty/unknown.
        if has_clinic_profile:
            return '/clinics/dashboard/'
        if has_patient_profile:
            return '/patients/dashboard/'
        return '/'



def google_start_view(request, role):
    if role not in {'patient', 'clinic'}:
        messages.error(request, 'Invalid Google account type selection.')
        return redirect('login')

    request.session['google_selected_role'] = role
    return redirect('/accounts/social/google/login/?process=login')

def custom_logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out successfully.')
    return redirect('login')

@login_required
def dashboard_redirect_view(request):
    user = request.user
    has_patient_profile, has_clinic_profile = _sync_user_type_from_profile(user)
    if user.user_type == 'patient':
        return redirect('patient_dashboard')
    elif user.user_type == 'clinic':
        return redirect('clinic_dashboard')
    if has_clinic_profile:
        return redirect('clinic_dashboard')
    if has_patient_profile:
        return redirect('patient_dashboard')
    else:
        messages.error(request, 'Unknown user type.')
        return redirect('login')