from django.shortcuts import render
from django.db.models import Q
from patients.models import Patient
from clinics.models import Clinic
from django.contrib.auth.decorators import login_required

@login_required
def search_all_view(request):
    query = request.GET.get('q', '') or ''
    query = query.strip()
    patient_results = []
    clinic_results = []
    if query:
        # split into tokens to support "name surname" and place searches
        tokens = [t for t in query.split() if t]

        # Patients: search full_name, username, and related medical record first/last names
        p_q = Q()
        for t in tokens:
            p_q |= Q(full_name__icontains=t)
            p_q |= Q(user__username__icontains=t)
            p_q |= Q(medical_records__first_name__icontains=t)
            p_q |= Q(medical_records__last_name__icontains=t)
        patient_results = Patient.objects.filter(p_q).distinct()[:50]

        # Clinics: search by clinic name only (requested dashboard behavior)
        c_q = Q()
        for t in tokens:
            c_q |= Q(clinic_name__icontains=t)
        clinic_results = Clinic.objects.filter(c_q).distinct()[:50]
    context = {
        'query': query,
        'patient_results': patient_results,
        'clinic_results': clinic_results,
    }
    return render(request, 'patient/dashboard/search_results.html', context)


@login_required
def search_patients_for_clinic_view(request):
    """Clinic-facing patient search: returns a partial HTML with patients only.
    Used by clinic dashboard search bar via AJAX.
    """
    query = request.GET.get('q', '') or ''
    query = query.strip()
    patient_results = []
    if query:
        tokens = [t for t in query.split() if t]
        p_q = Q()
        for t in tokens:
            p_q |= Q(full_name__icontains=t)
            p_q |= Q(user__username__icontains=t)
            p_q |= Q(medical_records__first_name__icontains=t)
            p_q |= Q(medical_records__last_name__icontains=t)
            p_q |= Q(phone__icontains=t)
        patient_results = Patient.objects.filter(p_q).distinct()[:50]

    context = {
        'query': query,
        'patient_results': patient_results,
    }
    return render(request, 'clinics/search_patients_results.html', context)
