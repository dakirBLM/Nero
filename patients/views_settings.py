from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Patient
from .forms import PatientForm, UserForm
from accounts.social_signals import sync_google_patient_avatar_for_user

@login_required
def patient_settings_view(request):
    if getattr(request.user, 'user_type', None) != 'patient':
        messages.error(request, 'This page is only available for patient accounts.')
        return redirect('dashboard_redirect')

    default_name = f"{request.user.first_name} {request.user.last_name}".strip() or request.user.username
    patient, _created = Patient.objects.get_or_create(
        user=request.user,
        defaults={
            'full_name': default_name,
            'gender': 'O',
            'phone': '0000000000',
        },
    )

    if not bool(getattr(patient.profile_picture, 'name', '')):
        if sync_google_patient_avatar_for_user(request.user):
            patient.refresh_from_db(fields=['profile_picture'])

    try:
        from allauth.socialaccount.models import SocialAccount
        google_connected = SocialAccount.objects.filter(user=request.user, provider='google').exists()
    except Exception:
        google_connected = False

    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        patient_form = PatientForm(request.POST, request.FILES, instance=patient)
        if user_form.is_valid() and patient_form.is_valid():
            user_form.save()
            patient_form.save()
            messages.success(request, 'Your account information has been updated!')
            return redirect('patient_settings')
    else:
        user_form = UserForm(instance=request.user)
        patient_form = PatientForm(instance=patient)
    return render(request, 'patient/patient_settings.html', {
        'user_form': user_form,
        'form': patient_form,
        'patient': patient,
        'google_connected': google_connected,
    })


@login_required
def connect_google_account_view(request):
    if getattr(request.user, 'user_type', None) != 'patient':
        messages.error(request, 'This action is only available for patient accounts.')
        return redirect('dashboard_redirect')

    request.session['google_selected_role'] = 'patient'
    return redirect('/accounts/social/google/login/?process=connect')
