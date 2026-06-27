from django.db import models
from clinics.models import Clinic
from patients.models import Patient

class Review(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='reviews')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='clinic_reviews')
    description = models.TextField()
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], help_text="Rating out of 5")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('clinic', 'patient')
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.patient} for {self.clinic} ({self.rating}/5)"
