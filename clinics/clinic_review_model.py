# Place ClinicReview at the very end of the file to avoid circular reference

class ClinicReview(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='reviews')
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='clinic_reviews')
    rating = models.PositiveSmallIntegerField(choices=[(i, str(i)) for i in range(1, 6)], help_text="Rating out of 5")
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('clinic', 'patient')  # One review per patient per clinic
        ordering = ['-created_at']

    def __str__(self):
        return f"Review by {self.patient} for {self.clinic} ({self.rating}/5)"
