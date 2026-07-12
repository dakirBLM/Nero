from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.conf import settings
from accounts.models import User
from .storage import EncryptedFileSystemStorage
from core.avatars import DEFAULT_AVATAR


def get_file_storage():
    """Return encrypted local file storage."""
    return EncryptedFileSystemStorage()


def validate_file_size_3mb(file_obj):
    limit = 3 * 1024 * 1024
    if file_obj and file_obj.size > limit:
        raise ValidationError('File too large. Size should not exceed 3 MB.')


def validate_file_size_50mb(file_obj):
    limit = 50 * 1024 * 1024
    if file_obj and file_obj.size > limit:
        raise ValidationError('File too large. Size should not exceed 50 MB.')

class Patient(models.Model):
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=30)
    profile_picture = models.FileField(
        upload_to='patient_profile_pics/',
        null=True,
        blank=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'png']),
            validate_file_size_3mb,
        ],
    )
    social_avatar_url = models.URLField(max_length=500, blank=True, default='', help_text="Avatar URL from a social login (e.g. Google).")
    last_seen = models.DateTimeField(null=True, blank=True)
    onboarding_done = models.BooleanField(default=False, help_text="First-run dashboard tour (King George onboarding) completed.")
    @property
    def age(self):
        from datetime import date
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )

    @property
    def avatar_url(self):
        """Best available avatar: social (Google CDN) → uploaded file → default SVG."""
        if self.social_avatar_url:
            return self.social_avatar_url
        try:
            if self.profile_picture and self.profile_picture.name:
                return self.profile_picture.url
        except Exception:
            pass
        return DEFAULT_AVATAR

    @property
    def has_custom_avatar(self):
        """True when there's a real avatar (uploaded file or social/Google URL)."""
        return bool(self.social_avatar_url) or bool(getattr(self.profile_picture, 'name', ''))

    def __str__(self):
        return self.full_name

    def is_active(self, minutes=5):
        from django.utils import timezone
        from datetime import timedelta
        if not self.last_seen:
            return False
        return timezone.now() - self.last_seen <= timedelta(minutes=minutes)

class MedicalRecord(models.Model):
    MOVEMENT_ABILITY_CHOICES = (
        ('independent', 'Independent'),
        ('assisted', 'Requires Assistance'),
        ('wheelchair', 'Wheelchair Bound'),
        ('bedridden', 'Bedridden'),
    )

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='medical_records')

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=Patient.GENDER_CHOICES)
    date_of_birth = models.DateField(null=False, blank=False)
    address = models.TextField(null=False, blank=False)
    country = models.CharField(max_length=100, null=False, blank=False)

    height = models.DecimalField(max_digits=5, decimal_places=2, help_text="Height in cm")
    weight = models.DecimalField(max_digits=5, decimal_places=2, help_text="Weight in kg")
    main_diagnosis = models.CharField(max_length=200)
    injury_date = models.DateField()
    movement_ability = models.CharField(max_length=20, choices=MOVEMENT_ABILITY_CHOICES)
    current_medications = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    previous_surgeries = models.TextField(blank=True)

    # Mobility aids
    uses_wheelchair = models.BooleanField(default=False)
    uses_walker = models.BooleanField(default=False)
    uses_crutch = models.BooleanField(default=False)
    uses_electric_wheelchair = models.BooleanField(default=False)

    # General patient condition
    bowel_control = models.BooleanField(default=True)
    urine_control = models.BooleanField(default=True)
    uses_permanent_catheter = models.BooleanField(default=False)
    uses_intermittent_catheter = models.BooleanField(default=False)
    uses_medical_condom = models.BooleanField(default=False)
    uses_diapers = models.BooleanField(default=False)
    can_breathe_normally = models.BooleanField(default=True)
    can_eat_independently = models.BooleanField(default=True)
    can_dress_independently = models.BooleanField(default=True)
    is_aware_and_cooperative = models.BooleanField(default=True)
    is_self_reliant = models.BooleanField(default=True)
    uses_feeding_tube = models.BooleanField(default=False)
    uses_stool_tube = models.BooleanField(default=False)
    uses_urine_tube = models.BooleanField(default=False)

    # Medical conditions
    has_bedsores = models.BooleanField(default=False)
    has_diabetes = models.BooleanField(default=False)
    uses_insulin = models.BooleanField(default=False)
    has_heart_problems = models.BooleanField(default=False)
    has_high_blood_pressure = models.BooleanField(default=False)
    has_infectious_diseases = models.BooleanField(default=False)
    has_vein_thrombosis = models.BooleanField(default=False)
    has_depression = models.BooleanField(default=False)

    # Contact fields
    email = models.EmailField(blank=True, null=True)
    mobile_number = models.CharField(max_length=20, blank=True, null=True)
    whatsapp_number = models.CharField(max_length=20, blank=True, null=True)

    # Uploads
    medical_reports = models.FileField(
        upload_to='medical_reports/',
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'png']),
            validate_file_size_3mb,
        ],
        storage=get_file_storage(),
    )

    patient_movement_video = models.FileField(
        upload_to='movement_videos/',
        blank=True,
        null=True,
        help_text="Upload a video showing patient's movement ability",
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4']),
            validate_file_size_50mb,
        ],
        storage=get_file_storage(),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Medical Record - {self.first_name} {self.last_name} ({self.main_diagnosis})"


class MedicalRecordReport(models.Model):
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='reports')
    file = models.FileField(
        upload_to='medical_reports/',
        validators=[
            FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png']),
            validate_file_size_3mb,
        ],
        storage=get_file_storage(),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Report #{self.id} for record {self.medical_record_id}"


class MedicalRecordVideo(models.Model):
    medical_record = models.ForeignKey(MedicalRecord, on_delete=models.CASCADE, related_name='videos')
    file = models.FileField(
        upload_to='movement_videos/',
        validators=[
            FileExtensionValidator(allowed_extensions=['mp4']),
            validate_file_size_50mb,
        ],
        storage=get_file_storage(),
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Video #{self.id} for record {self.medical_record_id}"
