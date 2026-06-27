from django.db.models.signals import post_delete
from django.dispatch import receiver

from clinics.models import Clinic, ClinicGallery, ClinicService, Post as ClinicPost
from patients.models import MedicalRecord, MedicalRecordReport, MedicalRecordVideo, Patient
from posts.models import Post as FeedPost


def _delete_field_file(field_file):
    """Delete a file from storage if it exists."""
    if not field_file:
        return

    file_name = getattr(field_file, 'name', '')
    if not file_name:
        return

    storage = field_file.storage
    try:
        if storage.exists(file_name):
            storage.delete(file_name)
    except Exception:
        # Ignore storage errors during cleanup to avoid blocking deletes.
        pass


@receiver(post_delete, sender=Patient)
def delete_patient_files(sender, instance, **kwargs):
    _delete_field_file(instance.profile_picture)


@receiver(post_delete, sender=MedicalRecord)
def delete_medical_record_files(sender, instance, **kwargs):
    _delete_field_file(instance.medical_reports)
    _delete_field_file(instance.patient_movement_video)


@receiver(post_delete, sender=MedicalRecordReport)
def delete_medical_record_report_file(sender, instance, **kwargs):
    _delete_field_file(instance.file)


@receiver(post_delete, sender=MedicalRecordVideo)
def delete_medical_record_video_file(sender, instance, **kwargs):
    _delete_field_file(instance.file)


@receiver(post_delete, sender=Clinic)
def delete_clinic_files(sender, instance, **kwargs):
    _delete_field_file(instance.profile_picture)
    _delete_field_file(instance.cover_photo)


@receiver(post_delete, sender=ClinicGallery)
def delete_clinic_gallery_image(sender, instance, **kwargs):
    _delete_field_file(instance.image)


@receiver(post_delete, sender=ClinicService)
def delete_clinic_service_photo(sender, instance, **kwargs):
    _delete_field_file(instance.photo)


@receiver(post_delete, sender=ClinicPost)
def delete_clinic_post_media(sender, instance, **kwargs):
    _delete_field_file(instance.image)
    _delete_field_file(instance.video)


@receiver(post_delete, sender=FeedPost)
def delete_feed_post_media(sender, instance, **kwargs):
    _delete_field_file(instance.image)
    _delete_field_file(instance.video)
