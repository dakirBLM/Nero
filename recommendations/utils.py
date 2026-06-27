from clinics.models import Clinic, ClinicService
from django.db.models import Avg
import re
import difflib
from django.db.models import Q


def _parse_price_range(text):
    """Parse a price string like '100-150', '$100 - $150', '<=80', '>=50', '50+' into (min, max).
    Returns (min_price, max_price) where either can be None if unbounded. Returns None if no numbers found.
    """
    if not text:
        return None
    s = str(text).lower()
    s = re.sub(r'[\$,]', '', s).strip()
    m = re.match(r'^(<=|<)\s*(\d+(?:\.\d+)?)$', s)
    if m:
        return (None, float(m.group(2)))
    m = re.match(r'^(>=|>)\s*(\d+(?:\.\d+)?)$', s)
    if m:
        return (float(m.group(2)), None)
    m = re.search(r'(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)', s)
    if m:
        return (float(m.group(1)), float(m.group(2)))
    m = re.match(r'^(\d+(?:\.\d+)?)\s*\+$', s)
    if m:
        return (float(m.group(1)), None)
    m = re.search(r'(\d+(?:\.\d+)?)', s)
    if m:
        v = float(m.group(1))
        return (v, v)
    return None


def _price_fits(preference, service_price_range):
    pref = _parse_price_range(preference)
    svc = _parse_price_range(service_price_range)
    if pref is None or svc is None:
        return False
    pref_min, pref_max = pref
    svc_min, svc_max = svc
    low_pref = pref_min if pref_min is not None else float('-inf')
    high_pref = pref_max if pref_max is not None else float('inf')
    low_svc = svc_min if svc_min is not None else float('-inf')
    high_svc = svc_max if svc_max is not None else float('inf')
    return not (high_svc < low_pref or low_svc > high_pref)


def recommend_clinics(params):
    """
    Production-grade, explainable scoring engine for matching patients with clinics.
    Returns list of dicts: {id, clinic_name, city, score, reasons, profile_picture}
    """
    services = params.get('services') or params.get('service') or ''
    if isinstance(services, str):
        services_list = [s.strip() for s in services.split(',') if s.strip()]
    else:
        services_list = [s.strip() for s in services]

    city = (params.get('city') or '').strip().lower()
    state = (params.get('state') or params.get('county') or '').strip().lower()
    price_pref = (params.get('price') or '').strip()

    # Scoring weights adjusted per user request:
    # - Exact service match: +6 points
    # - Partial service match: +2 points
    # - City/address match: +5 points
    # - Each review star adds 1 point (review_avg)
    # - If years in operation > 5, add +1 point
    SERVICE_EXACT = 6.0
    SERVICE_PARTIAL = 2.0
    CITY_MATCH = 5.0

    compatible_clinics = params.get('compatible_clinics')
    if compatible_clinics is not None:
        clinics = compatible_clinics
    else:
        # Prefetch services and reviews to allow computing review aggregates without extra queries
        clinics = Clinic.objects.all().prefetch_related('services', 'reviews')

    results = []
    for c in clinics:
        score = 0.0
        reasons = []

        svc_objs = list(c.services.all())
        matched_services = []
        price_fit_found = False
        for requested in services_list:
            rq = requested.lower()
            best_local = 0.0
            for svc in svc_objs:
                name = (svc.service_name or '').lower()
                desc = (svc.description or '').lower()
                if rq == name:
                    best_local = max(best_local, SERVICE_EXACT)
                    matched_services.append((requested, svc))
                elif rq in name or rq in desc:
                    best_local = max(best_local, SERVICE_PARTIAL)
                    matched_services.append((requested, svc))
                if price_pref and _price_fits(price_pref, svc.price_range):
                    price_fit_found = True
            if best_local > 0:
                score += best_local
                reasons.append(f"Service match: {requested} (+{best_local})")

        if services_list and not matched_services:
            reasons.append("No exact or partial service matches")

        # City/address match (strong preference).
        # Use case-insensitive containment and fuzzy matching against the
        # patient location (either provided via params['city'] or extracted
        # from the medical record fields).
        clinic_city = (c.city or '').lower().strip()

        # Build a patient location string to compare against
        patient_loc = ''
        if city:
            patient_loc = str(city).lower().strip()
        else:
            mr = params.get('medical_record')
            if mr is not None:
                parts = []
                for attr in ('address', 'full_address', 'city', 'location', 'residence', 'home_address', 'postal_code'):
                    try:
                        val = getattr(mr, attr, None)
                    except Exception:
                        val = None
                    if val:
                        parts.append(str(val))
                patient_loc = ' '.join(parts).lower().strip()

        # Normalize by removing punctuation
        if patient_loc:
            patient_loc = re.sub(r'[^a-z0-9\s]', ' ', patient_loc)
            patient_loc = re.sub(r'\s+', ' ', patient_loc).strip()

        matched_city = False
        if clinic_city and patient_loc:
            if clinic_city == patient_loc or clinic_city in patient_loc or patient_loc in clinic_city:
                matched_city = True
            else:
                # Fuzzy match full strings
                try:
                    ratio = difflib.SequenceMatcher(None, clinic_city, patient_loc).ratio()
                except Exception:
                    ratio = 0.0
                if ratio >= 0.75:
                    matched_city = True
                else:
                    # Check tokens in the patient location
                    for tok in patient_loc.split():
                        if not tok:
                            continue
                        if clinic_city == tok or clinic_city in tok or tok in clinic_city:
                            matched_city = True
                            break
                        try:
                            r = difflib.SequenceMatcher(None, clinic_city, tok).ratio()
                        except Exception:
                            r = 0.0
                        if r >= 0.8:
                            matched_city = True
                            break

        if matched_city:
            score += CITY_MATCH
            reasons.append(f"Located in {c.city} (+{CITY_MATCH})")

        # Add review average directly as points: each star = 1 point
        try:
            review_avg = round((c.reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0), 2) if hasattr(c, 'reviews') else 0.0
        except Exception:
            review_avg = 0.0
        if review_avg:
            score += float(review_avg)
            reasons.append(f'Review average: {review_avg} stars (+{review_avg})')

        # Years of experience: if > 5 years, add +1
        try:
            years = float(c.years_in_operation or 0)
            if years > 5:
                score += 1.0
                reasons.append(f'Established {int(years)} years (+1)')
        except Exception:
            pass

        results.append({
            'id': c.id,
            'clinic_name': c.clinic_name,
            'city': c.city,
            'score': round(score, 4),
            # Compute review aggregates (avg rating and total count)
            'review_avg': round((c.reviews.aggregate(avg=Avg('rating'))['avg'] or 0.0), 2) if hasattr(c, 'reviews') else 0.0,
            'review_count': c.reviews.count() if hasattr(c, 'reviews') else 2,
            'reasons': reasons,
            'profile_picture': c.profile_picture.url if c.profile_picture else None,
        })

    results.sort(key=lambda x: x['score'], reverse=True)
    return results


def simple_clinic_score(params):
    """Backward-compatible wrapper used by the questionnaire view.
    For now it delegates to recommend_clinics to keep results consistent.
    """
    return recommend_clinics(params)
