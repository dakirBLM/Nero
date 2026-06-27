
from django.db import models
from accounts.models import User
from patients.models import MedicalRecord, Patient
from core.validators import validate_video_extension, validate_video_size


class Post(models.Model):
    clinic = models.ForeignKey('Clinic', on_delete=models.CASCADE, related_name='clinic_posts')
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='clinic_post_authors')
    description = models.TextField()
    image = models.ImageField(upload_to='clinic_posts/', blank=True, null=True)
    video = models.FileField(
        upload_to='clinic_post_videos/',
        blank=True,
        null=True,
        validators=[validate_video_extension, validate_video_size],
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=['clinic', '-created_at'])]

    def __str__(self):
        return f"Post by {self.author} for {self.clinic.clinic_name}"



class Clinic(models.Model):
    SPECIALIZATION_CHOICES = (
        ('Convalescence', 'Convalescence'),
        ('Weight loss', 'Weight loss'),
        ('Musculoskeletal treatment', 'Musculoskeletal treatment'),
        ('Neurological treatment', 'Neurological treatment'),
    )

    CLINIC_TYPE_CHOICES = (
        ('Convalescence', 'Convalescence'),
        ('Weight loss', 'Weight loss'),
        ('Musculoskeletal treatment', 'Musculoskeletal treatment'),
        ('Neurological treatment', 'Neurological treatment'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    clinic_name = models.CharField(max_length=200)
    tagline = models.CharField(max_length=300, blank=True, help_text="Brief tagline for your clinic")
    description = models.TextField(help_text="Detailed description of your clinic services and approach")
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    country = models.CharField(max_length=100, blank=True, default='')
    continent = models.CharField(max_length=100, blank=True, default='')
    clinic_type = models.CharField(max_length=255, blank=True, default='', help_text="Selected clinic types (comma separated)")
    zip_code = models.CharField(max_length=20)
    phone_number = models.CharField(max_length=30)
    contact_email = models.EmailField()
    website = models.URLField(blank=True)
    google_maps_url = models.URLField(max_length=1000, blank=True, help_text="Google Maps embed URL (from Share → Embed a map → Copy src URL)")
    specialization = models.TextField(help_text="Primary specialization(s) (comma separated)")
    established_date = models.DateField()
    facilities = models.CharField(max_length=500, blank=True, help_text="Available facilities (comma separated)")
    number_of_therapists = models.PositiveIntegerField(default=1)
    languages_spoken = models.CharField(max_length=200, default='English', help_text="Languages spoken (comma separated)")
    hours_of_operation = models.TextField(default='Mon-Fri: 9:00 AM - 6:00 PM\nSat: 9:00 AM - 1:00 PM')
    profile_picture = models.ImageField(upload_to='clinic_profile_pics/', blank=True, null=True, help_text="Main profile picture of your clinic")
    cover_photo = models.ImageField(upload_to='clinic_cover_photos/', blank=True, null=True, help_text="Cover photo for your clinic page")
    last_seen = models.DateTimeField(null=True, blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    is_verified = models.BooleanField(default=False)
    # Acceptance flags: whether the clinic accepts certain patient conditions
    accepts_heart_problems = models.BooleanField(default=True, help_text="Accept patients with heart problems")
    accepts_catheter = models.BooleanField(default=True, help_text="Accept patients using a catheter (permanent or intermittent)")
    accepts_wheelchair = models.BooleanField(default=True, help_text="Accept patients who use a wheelchair")
    accepts_walker = models.BooleanField(default=True, help_text="Accept patients who use a walker")
    accepts_crutch = models.BooleanField(default=True, help_text="Accept patients who use crutches")
    accepts_electric_wheelchair = models.BooleanField(default=True, help_text="Accept patients who use an electric wheelchair")
    accepts_bowel_incontinence = models.BooleanField(default=True, help_text="Accept patients with bowel incontinence")
    accepts_urine_incontinence = models.BooleanField(default=True, help_text="Accept patients with urine incontinence")
    accepts_medical_condom = models.BooleanField(default=True, help_text="Accept patients using a medical condom")
    accepts_diapers = models.BooleanField(default=True, help_text="Accept patients using diapers")
    accepts_breathing_issues = models.BooleanField(default=True, help_text="Accept patients with breathing issues")
    accepts_feeding_tube = models.BooleanField(default=True, help_text="Accept patients using a feeding tube")
    accepts_stool_tube = models.BooleanField(default=True, help_text="Accept patients using a stool tube")
    accepts_urine_tube = models.BooleanField(default=True, help_text="Accept patients using a urine tube")
    accepts_bedsores = models.BooleanField(default=True, help_text="Accept patients with bedsores")
    accepts_diabetes = models.BooleanField(default=True, help_text="Accept patients with diabetes")
    accepts_insulin = models.BooleanField(default=True, help_text="Accept patients using insulin")
    accepts_high_blood_pressure = models.BooleanField(default=True, help_text="Accept patients with high blood pressure")
    accepts_infectious_diseases = models.BooleanField(default=True, help_text="Accept patients with infectious diseases")
    accepts_vein_thrombosis = models.BooleanField(default=True, help_text="Accept patients with vein thrombosis")
    accepts_depression = models.BooleanField(default=True, help_text="Accept patients with depression")
    
    def __str__(self):
        return self.clinic_name

    def is_active(self, minutes=5):
        from django.utils import timezone
        from datetime import timedelta
        if not self.last_seen:
            return False
        return timezone.now() - self.last_seen <= timedelta(minutes=minutes)
    
    @property
    def full_address(self):
        return f"{self.address}, {self.city}, {self.state} {self.zip_code}"
    
    def get_average_rating(self):
        """Calculate average rating from all reviews for this clinic."""
        reviews = self.reviews.all()
        if not reviews.exists():
            return None
        return round(sum(review.rating for review in reviews) / reviews.count(), 1)
    
    @property
    def years_in_operation(self):
        from datetime import date
        return date.today().year - self.established_date.year

class ClinicGallery(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='clinic_gallery/')
    caption = models.CharField(max_length=200, blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Gallery image for {self.clinic.clinic_name}"

class ClinicService(models.Model):
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE, related_name='services')
    service_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    photo = models.ImageField(upload_to='clinic_services/', blank=True, null=True)
    price_range = models.CharField(max_length=100, blank=True, help_text="e.g., $100-$150 per session")
    
    def __str__(self):
        return f"{self.service_name} - {self.clinic.clinic_name}"
    
class Appointment(models.Model):
    # Full appointment status lifecycle (8 states)
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted_record_accepted_accommodation', 'Accepted - Record & Accommodation Accepted'),
        ('accepted_record_accommodation_change_requested', 'Accepted - Accommodation Change Requested'),
        ('rejected_medical_record', 'Rejected - Medical Record Declined'),
        ('cancelled', 'Cancelled'),
        ('waiting_for_payment', 'Waiting for Payment'),
        ('paid', 'Paid'),
        ('upcoming', 'Upcoming'),
    ]

    MEDICAL_REJECTION_REASON_CHOICES = [
        ('not_a_match', 'Not aligned with clinic specialization'),
        ('capacity_unavailable', 'No clinical capacity in requested timeline'),
        ('missing_information', 'Insufficient medical information'),
        ('medical_complexity', 'Case complexity beyond current capability'),
        ('safety_concerns', 'Patient safety concerns'),
        ('other', 'Other'),
    ]

    ROOM_TYPE_CHOICES = [
        ('single', 'Single Room'),
        ('double', 'Double Room'),
        ('suite', 'Suite'),
    ]

    ACCOMMODATION_TYPE_CHOICES = [
        ('single_room', 'Single room'),
        ('double_room', 'Double room'),
        ('double_suite', 'Double suite'),
        ('quad_suite', 'Quad suite'),
        ('no_accommodation', 'No accommodation'),
    ]

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    clinic = models.ForeignKey(Clinic, on_delete=models.CASCADE)
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE)
    appointment_date = models.DateField(null=True, blank=True)
    appointment_time = models.TimeField(null=True, blank=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    medical_record_accepted = models.BooleanField(default=False)
    medical_rejection_reason = models.CharField(max_length=40, choices=MEDICAL_REJECTION_REASON_CHOICES, blank=True, default='')
    needs_accommodation = models.BooleanField(default=False)
    companions_count = models.PositiveIntegerField(null=True, blank=True)
    accommodation_type = models.CharField(max_length=30, choices=ACCOMMODATION_TYPE_CHOICES, blank=True, default='')
    travelers_count = models.PositiveIntegerField(null=True, blank=True)
    preferred_room_type = models.CharField(max_length=20, choices=ROOM_TYPE_CHOICES, blank=True, default='')
    treatment_start_date = models.DateField(null=True, blank=True)
    treatment_end_date = models.DateField(null=True, blank=True)
    proposed_start_date = models.DateField(null=True, blank=True)
    proposed_end_date = models.DateField(null=True, blank=True)
    clinic_proposal_note = models.TextField(blank=True, default='', help_text="Clinic's proposed changes to accommodation/dates")
    patient_response_note = models.TextField(blank=True, default='', help_text="Patient's response to clinic's proposed changes")
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    payment_due_at = models.DateTimeField(null=True, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True, help_text="Timestamp when payment was confirmed")
    requested_service = models.CharField(max_length=200, blank=True, default='')
    requested_country = models.CharField(max_length=100, blank=True, default='')
    requested_continent = models.CharField(max_length=100, blank=True, default='')
    requested_clinic_type = models.CharField(max_length=200, blank=True, default='')
    notes = models.TextField(blank=True, help_text="Any additional notes for the clinic")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['clinic', 'status']),
            models.Index(fields=['patient', 'status']),
        ]

    def __str__(self):
        return f"Appointment: {self.patient.full_name} - {self.clinic.clinic_name} - {self.appointment_date}"

    # Helper properties for template compatibility
    @property
    def medical_review_status(self):
        """Read-only property for template compatibility"""
        if self.status == 'rejected_medical_record':
            return 'rejected'
        elif self.status in ['accepted_record_accepted_accommodation', 'accepted_record_accommodation_change_requested', 'waiting_for_payment', 'paid', 'upcoming', 'cancelled']:
            return 'accepted'
        elif self.medical_record_accepted:
            return 'accepted'
        elif self.status == 'pending':
            return 'pending'
        else:
            return 'accepted'

    @property
    def accommodation_review_status(self):
        """Read-only property for template compatibility"""
        if not self.needs_accommodation:
            return 'not_required'
        elif self.status in ['accepted_record_accepted_accommodation', 'waiting_for_payment', 'paid', 'upcoming']:
            return 'accepted_with'
        else:
            return 'pending'

    @property
    def facility_response(self):
        """Read-only property for template compatibility"""
        if self.status == 'rejected_medical_record':
            return 'reject_booking'
        elif self.status == 'accepted_record_accommodation_change_requested':
            return 'accept_propose_different_dates'
        elif self.status in ['accepted_record_accepted_accommodation', 'waiting_for_payment', 'paid', 'upcoming']:
            return 'accept_requested_dates'
        else:
            return 'pending'

    def get_medical_review_status_display(self):
        """Return display name for medical_review_status"""
        status_display_map = {
            'pending': 'Pending Medical Review',
            'accepted': 'Medical Record Accepted',
            'rejected': 'Medical Record Rejected',
        }
        return status_display_map.get(self.medical_review_status, 'Unknown')