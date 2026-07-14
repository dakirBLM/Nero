import json

from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages


def _get_patient_for_request(request):
    from patients.models import Patient

    if not getattr(request.user, 'is_authenticated', False):
        return None
    if getattr(request.user, 'user_type', None) != 'patient':
        return None
    try:
        return Patient.objects.get(user=request.user)
    except Patient.DoesNotExist:
        return None


def _medical_compatible_clinics(medical_record, queryset=None):
    """Return clinics compatible with key medical constraints from the record."""
    from clinics.models import Clinic

    clinics_qs = queryset if queryset is not None else Clinic.objects.all()
    compatible = []
    for clinic in clinics_qs:
        incompatible = False

        if getattr(medical_record, 'has_heart_problems', False) and not clinic.accepts_heart_problems:
            incompatible = True

        if (
            getattr(medical_record, 'uses_permanent_catheter', False)
            or getattr(medical_record, 'uses_intermittent_catheter', False)
            or getattr(medical_record, 'uses_urine_tube', False)
        ) and not clinic.accepts_catheter:
            incompatible = True

        if getattr(medical_record, 'uses_wheelchair', False) and not clinic.accepts_wheelchair:
            incompatible = True
        if getattr(medical_record, 'uses_walker', False) and not clinic.accepts_walker:
            incompatible = True
        if getattr(medical_record, 'uses_crutch', False) and not clinic.accepts_crutch:
            incompatible = True
        if getattr(medical_record, 'uses_electric_wheelchair', False) and not clinic.accepts_electric_wheelchair:
            incompatible = True

        if not getattr(medical_record, 'bowel_control', True) and not clinic.accepts_bowel_incontinence:
            incompatible = True
        if not getattr(medical_record, 'urine_control', True) and not clinic.accepts_urine_incontinence:
            incompatible = True

        if getattr(medical_record, 'uses_medical_condom', False) and not clinic.accepts_medical_condom:
            incompatible = True
        if getattr(medical_record, 'uses_diapers', False) and not clinic.accepts_diapers:
            incompatible = True

        if not getattr(medical_record, 'can_breathe_normally', True) and not clinic.accepts_breathing_issues:
            incompatible = True

        if getattr(medical_record, 'uses_feeding_tube', False) and not clinic.accepts_feeding_tube:
            incompatible = True
        if getattr(medical_record, 'uses_stool_tube', False) and not clinic.accepts_stool_tube:
            incompatible = True
        if getattr(medical_record, 'uses_urine_tube', False) and not clinic.accepts_urine_tube:
            incompatible = True

        if getattr(medical_record, 'has_bedsores', False) and not clinic.accepts_bedsores:
            incompatible = True
        if getattr(medical_record, 'has_diabetes', False) and not clinic.accepts_diabetes:
            incompatible = True
        if getattr(medical_record, 'uses_insulin', False) and not clinic.accepts_insulin:
            incompatible = True
        if getattr(medical_record, 'has_high_blood_pressure', False) and not clinic.accepts_high_blood_pressure:
            incompatible = True
        if getattr(medical_record, 'has_infectious_diseases', False) and not clinic.accepts_infectious_diseases:
            incompatible = True
        if getattr(medical_record, 'has_vein_thrombosis', False) and not clinic.accepts_vein_thrombosis:
            incompatible = True
        if getattr(medical_record, 'has_depression', False) and not clinic.accepts_depression:
            incompatible = True

        if not incompatible:
            compatible.append(clinic)

    return compatible


COUNTRY_TO_CONTINENT = {
    'czech republic': 'Europe',
    'czechia': 'Europe',
    'germany': 'Europe',
    'france': 'Europe',
    'italy': 'Europe',
    'spain': 'Europe',
    'portugal': 'Europe',
    'netherlands': 'Europe',
    'belgium': 'Europe',
    'switzerland': 'Europe',
    'austria': 'Europe',
    'sweden': 'Europe',
    'norway': 'Europe',
    'denmark': 'Europe',
    'poland': 'Europe',
    'romania': 'Europe',
    'greece': 'Europe',
    'turkey': 'Europe',
    'united kingdom': 'Europe',
    'uk': 'Europe',
    'ireland': 'Europe',
    'usa': 'North America',
    'united states': 'North America',
    'canada': 'North America',
    'mexico': 'North America',
    'morocco': 'Africa',
    'tunisia': 'Africa',
    'algeria': 'Africa',
    'egypt': 'Africa',
    'south africa': 'Africa',
    'nigeria': 'Africa',
    'kenya': 'Africa',
    'india': 'Asia',
    'china': 'Asia',
    'japan': 'Asia',
    'south korea': 'Asia',
    'saudi arabia': 'Asia',
    'uae': 'Asia',
    'united arab emirates': 'Asia',
    'qatar': 'Asia',
    'australia': 'Oceania',
    'new zealand': 'Oceania',
    'brazil': 'South America',
    'argentina': 'South America',
    'chile': 'South America',
    'colombia': 'South America',
    'peru': 'South America',
}


def _infer_continent_from_country(country):
    if not country:
        return ''
    return COUNTRY_TO_CONTINENT.get(country.strip().lower(), '')


def _normalized_clinic_continent(clinic):
    return (clinic.continent or '').strip() or _infer_continent_from_country((clinic.country or '').strip())


def _build_clinic_filter_data():
    from clinics.models import Clinic

    clinics = Clinic.objects.prefetch_related('services').all()
    rows = []
    for clinic in clinics:
        continent = _normalized_clinic_continent(clinic)
        services = [s.service_name.strip() for s in clinic.services.all() if s.service_name and s.service_name.strip()]
        rows.append(
            {
                'id': clinic.id,
                'continent': continent,
                'country': (clinic.country or '').strip(),
                'clinic_type': (clinic.clinic_type or '').strip(),
                'services': sorted(set(services)),
            }
        )
    return rows


def _compute_service_match(clinic, selected_service):
    """Return (match_points, matched_service_names) for a clinic and requested service text."""
    score = 0
    matched_service_names = []

    selected_service = (selected_service or '').strip()
    if not selected_service:
        return score, matched_service_names

    clinic_services = list(clinic.services.all())
    all_service_text = ' '.join(
        [
            f"{(svc.service_name or '').lower()} {(svc.description or '').lower()}".strip()
            for svc in clinic_services
        ]
    )
    query_l = selected_service.lower()
    service_terms = [t.strip().lower() for t in selected_service.replace(',', ' ').split() if t.strip()]

    # Exact phrase match in combined services text
    if query_l and query_l in all_service_text:
        score += 6

    # Service-level match tracking
    for svc in clinic_services:
        svc_name = (svc.service_name or '').strip()
        svc_text = f"{(svc.service_name or '').lower()} {(svc.description or '').lower()}".strip()
        if not svc_name:
            continue
        if query_l and query_l in svc_text:
            matched_service_names.append(svc_name)
            continue
        for term in service_terms:
            if term in svc_text:
                matched_service_names.append(svc_name)
                break

    # Token-level relevance score
    token_hits = 0
    for term in service_terms:
        if term in all_service_text:
            token_hits += 1
    score += min(token_hits * 2, 10)

    return score, sorted(set(matched_service_names))


def _base_filter_context(patient, preselected_record_id=''):
    from patients.models import MedicalRecord
    from clinics.models import Clinic

    medical_records = MedicalRecord.objects.filter(patient=patient).order_by('-updated_at') if patient else []
    clinic_filter_data = _build_clinic_filter_data()
    continents = sorted({row['continent'] for row in clinic_filter_data if row['continent']})

    clinic_types = [choice[0] for choice in Clinic.CLINIC_TYPE_CHOICES]
    # Display labels (translated); submitted values stay the English choice keys.
    clinic_type_labels = [str(choice[1]) for choice in Clinic.CLINIC_TYPE_CHOICES]

    return {
        'patient': patient,
        'medical_records': medical_records,
        'services': [],
        'countries': [],
        'continents': continents,
        'clinic_types': clinic_types,
        'clinic_type_labels': clinic_type_labels,
        'clinic_filter_data_json': json.dumps(clinic_filter_data),
        'preselected_record_id': str(preselected_record_id or ''),
    }


@login_required
@require_http_methods(["GET"])
def questionnaire_view(request):
    """Step 1 + Step 2 UI for medical tourism request flow."""
    patient = _get_patient_for_request(request)
    if not patient:
        messages.error(request, 'Only patients can submit clinic requests.')
        return redirect('login')

    # Arriving here completes the first-run King George onboarding tour.
    if not getattr(patient, 'onboarding_done', True):
        patient.onboarding_done = True
        patient.save(update_fields=['onboarding_done'])

    preselected_record_id = request.GET.get('medical_record_id', '')
    context = _base_filter_context(patient, preselected_record_id)
    return render(request, 'recommendations/questionnaire.html', context)


@login_required
@require_http_methods(["POST"])
def recommendation_result_view(request):
    """Step 3: filter clinics and show selectable result cards."""
    from clinics.models import Clinic
    from patients.models import MedicalRecord

    patient = _get_patient_for_request(request)
    if not patient:
        messages.error(request, 'Only patients can submit clinic requests.')
        return redirect('login')

    record_id = (request.POST.get('medical_record_id') or '').strip()
    selected_service = (request.POST.get('service') or '').strip()
    selected_continents_raw = [v.strip() for v in request.POST.getlist('continent') if v and v.strip()]
    selected_countries_raw = [v.strip() for v in request.POST.getlist('country') if v and v.strip()]

    all_continents_selected = any(v.lower() == 'all' for v in selected_continents_raw)
    all_countries_selected = any(v.lower() == 'all' for v in selected_countries_raw)

    selected_continents = [] if all_continents_selected else selected_continents_raw
    selected_countries = [] if all_countries_selected else selected_countries_raw
    selected_clinic_types = [v.strip() for v in request.POST.getlist('clinic_type') if v and v.strip()]

    if not selected_clinic_types:
        selected_clinic_types = [choice[0] for choice in Clinic.CLINIC_TYPE_CHOICES]

    selected_record = MedicalRecord.objects.filter(id=record_id, patient=patient).first()
    if not selected_record:
        messages.error(request, 'Please select a valid medical record before continuing.')
        return redirect('recommendations:questionnaire')

    # STEP 1: Filter by medical compatibility - only show clinics that accept ALL patient conditions
    compatible = _medical_compatible_clinics(selected_record)
    compatible_ids = [clinic.id for clinic in compatible]
    clinics = Clinic.objects.filter(id__in=compatible_ids)

    # STEP 2: Apply geographic and clinic type filters
    if selected_countries:
        from django.db.models import Q

        country_query = Q()
        for c in selected_countries:
            country_query |= Q(country__iexact=c)
        clinics = clinics.filter(country_query)

    if selected_clinic_types:
        from django.db.models import Q

        type_query = Q()
        for t in selected_clinic_types:
            type_query |= Q(clinic_type__icontains=t) | Q(specialization__icontains=t)
        clinics = clinics.filter(type_query)

    clinics = clinics.distinct().prefetch_related('services').order_by('clinic_name')

    if selected_continents:
        selected_continent_l = {c.lower() for c in selected_continents}
        clinics = [
            clinic
            for clinic in clinics
            if _normalized_clinic_continent(clinic).lower() in selected_continent_l
        ]

    # STEP 3: Score compatible clinics ONLY on treatment/service matching
    # Clinics that don't match patient's medical conditions are already filtered out
    scored_clinics = []
    for clinic in clinics:
        score, matched_service_names = _compute_service_match(clinic, selected_service)

        clinic.match_points = score
        clinic.matched_services = matched_service_names

        # When a service is provided, hide clinics with zero service match score.
        if selected_service and score <= 0:
            continue

        scored_clinics.append(clinic)

    # Sort by match score (service matching) - higher scores first
    scored_clinics.sort(key=lambda c: (getattr(c, 'match_points', 0), c.clinic_name.lower()), reverse=True)

    # Add rating to each clinic
    for clinic in scored_clinics:
        clinic.rating = clinic.get_average_rating()

    context = _base_filter_context(patient, selected_record.id)
    accommodation_type = (request.POST.get('accommodation_type') or '').strip()
    companions_count = (request.POST.get('companions_count') or '').strip()
    treatment_start_date = (request.POST.get('treatment_start_date') or '').strip()
    treatment_end_date = (request.POST.get('treatment_end_date') or '').strip()
    context.update(
        {
            'results': scored_clinics,
            'match_count': len(scored_clinics),
            'matched_clinic_ids': [c.id for c in scored_clinics],
            'has_searched': True,
            'selected_record': selected_record,
            'form_data': {
                'medical_record_id': str(selected_record.id),
                'service': selected_service,
                'countries': (['all'] if all_countries_selected else selected_countries),
                'continents': (['all'] if all_continents_selected else selected_continents),
                'clinic_types': selected_clinic_types,
                'accommodation_type': accommodation_type,
                'companions_count': companions_count,
                'treatment_start_date': treatment_start_date,
                'treatment_end_date': treatment_end_date,
            },
        }
    )
    return render(request, 'recommendations/questionnaire.html', context)


@login_required
@require_http_methods(["POST"])
def send_appointment_requests_view(request):
    """Step 4: create pending appointment requests for all selected clinics."""
    from clinics.models import Appointment, Clinic
    from patients.models import MedicalRecord

    patient = _get_patient_for_request(request)
    if not patient:
        messages.error(request, 'Only patients can submit clinic requests.')
        return redirect('login')

    record_id = (request.POST.get('medical_record_id') or '').strip()
    selected_record = MedicalRecord.objects.filter(id=record_id, patient=patient).first()
    if not selected_record:
        messages.error(request, 'Medical record is missing or invalid.')
        return redirect('recommendations:questionnaire')

    selected_ids = request.POST.getlist('all_result_clinics')
    if not selected_ids:
        # Backward compatibility with older UI that allowed manual selection.
        selected_ids = request.POST.getlist('selected_clinics')
    selected_ids = list(dict.fromkeys([str(v).strip() for v in selected_ids if str(v).strip()]))
    if not selected_ids:
        messages.error(request, 'No matching clinics were found for dispatch.')
        return redirect('recommendations:questionnaire')

    selected_service = (request.POST.get('service') or '').strip()
    selected_countries_raw = [v.strip() for v in request.POST.getlist('country') if v and v.strip()]
    selected_continents_raw = [v.strip() for v in request.POST.getlist('continent') if v and v.strip()]
    selected_clinic_types = [v.strip() for v in request.POST.getlist('clinic_type') if v and v.strip()]
    selected_clinic_type = ', '.join(selected_clinic_types)
    selected_country = ', '.join(selected_countries_raw) if selected_countries_raw else ''
    selected_continent = ', '.join(selected_continents_raw) if selected_continents_raw else ''

    accommodation_type = (request.POST.get('accommodation_type') or '').strip()
    companions_raw = (request.POST.get('companions_count') or '').strip()
    treatment_start_raw = (request.POST.get('treatment_start_date') or '').strip()
    treatment_end_raw = (request.POST.get('treatment_end_date') or '').strip()

    room_type_map = {
        'single_room': 'single',
        'double_room': 'double',
        'double_suite': 'suite',
        'quad_suite': 'suite',
        'no_accommodation': '',
    }
    valid_accommodation_types = dict(Appointment.ACCOMMODATION_TYPE_CHOICES)
    if accommodation_type and accommodation_type not in valid_accommodation_types:
        accommodation_type = ''

    needs_accommodation = bool(accommodation_type and accommodation_type != 'no_accommodation')
    companions_count = None
    if companions_raw.isdigit() and int(companions_raw) >= 0:
        companions_count = int(companions_raw)
    elif needs_accommodation:
        companions_count = 0

    treatment_start_date = None
    treatment_end_date = None
    if treatment_start_raw and treatment_end_raw:
        from datetime import datetime
        try:
            treatment_start_date = datetime.strptime(treatment_start_raw, '%Y-%m-%d').date()
            treatment_end_date = datetime.strptime(treatment_end_raw, '%Y-%m-%d').date()
            if treatment_end_date < treatment_start_date:
                treatment_start_date = None
                treatment_end_date = None
        except ValueError:
            treatment_start_date = None
            treatment_end_date = None

    compatible = _medical_compatible_clinics(selected_record, Clinic.objects.filter(id__in=selected_ids).prefetch_related('services'))

    # Enforce service matching at dispatch time too, to prevent booking a clinic
    # with zero service points via tampered form submissions.
    if selected_service:
        filtered = []
        for clinic in compatible:
            score, _matched = _compute_service_match(clinic, selected_service)
            if score > 0:
                filtered.append(clinic)
        compatible = filtered

    compatible_map = {str(c.id): c for c in compatible}

    created_count = 0
    skipped_count = 0

    for clinic_id in selected_ids:
        clinic = compatible_map.get(str(clinic_id))
        if not clinic:
            skipped_count += 1
            continue

        already_open = Appointment.objects.filter(
            patient=patient,
            clinic=clinic,
            medical_record=selected_record,
            status__in=['pending', 'accepted', 'awaiting_accommodation', 'payment_pending', 'clinic_date_change_proposed', 'patient_date_change_requested'],
        ).exists()
        if already_open:
            skipped_count += 1
            continue

        Appointment.objects.create(
            patient=patient,
            clinic=clinic,
            medical_record=selected_record,
            appointment_date=None,
            appointment_time=None,
            status='pending',
            needs_accommodation=needs_accommodation,
            companions_count=companions_count,
            accommodation_type=accommodation_type,
            travelers_count=companions_count if needs_accommodation else None,
            preferred_room_type=room_type_map.get(accommodation_type, ''),
            treatment_start_date=treatment_start_date,
            treatment_end_date=treatment_end_date,
            proposed_start_date=None,
            proposed_end_date=None,
            requested_service=selected_service,
            requested_country=selected_country,
            requested_continent=selected_continent,
            requested_clinic_type=selected_clinic_type,
            notes='',
        )
        created_count += 1

    if created_count:
        messages.success(request, 'Your medical record has been sent to matching clinics.')
    if skipped_count:
        messages.warning(request, f'{skipped_count} clinic(s) were skipped (already requested or incompatible).')

    return redirect('patient_appointments')
