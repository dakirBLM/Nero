from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Avg
from .models import Review
from clinics.models import Clinic
from patients.models import Patient

@login_required
def submit_review(request, clinic_id):
    clinic = get_object_or_404(Clinic, id=clinic_id)
    patient = get_object_or_404(Patient, user=request.user)
    if request.method == 'POST':
        description = request.POST.get('review_description', '').strip()
        rating = request.POST.get('review_rating')
        if not description or not rating:
            messages.error(request, 'Please provide both a review and a rating.')
        else:
            try:
                rating = int(rating)
                if rating < 1 or rating > 5:
                    raise ValueError
            except ValueError:
                messages.error(request, 'Invalid rating value.')
            else:
                Review.objects.update_or_create(
                    clinic=clinic, patient=patient,
                    defaults={'description': description, 'rating': rating}
                )
                messages.success(request, 'Review submitted!')
        return redirect('clinic_detail', clinic_id=clinic.id)
    return redirect('clinic_detail', clinic_id=clinic.id)
