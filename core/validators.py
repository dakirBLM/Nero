"""Reusable file-upload validators."""
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# Allowed video container formats for clinic post/feed uploads.
ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'm4v']

validate_video_extension = FileExtensionValidator(allowed_extensions=ALLOWED_VIDEO_EXTENSIONS)


def validate_video_size(file_obj, max_mb=50):
    """Reject uploaded videos larger than `max_mb` megabytes."""
    if file_obj and file_obj.size > max_mb * 1024 * 1024:
        raise ValidationError(f'Video too large. Maximum size is {max_mb} MB.')
