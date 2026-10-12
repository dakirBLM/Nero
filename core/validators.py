"""Reusable file-upload validators."""
from datetime import date

from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _

# Allowed video container formats for clinic post/feed uploads.
ALLOWED_VIDEO_EXTENSIONS = ['mp4', 'webm', 'mov', 'm4v']

validate_video_extension = FileExtensionValidator(allowed_extensions=ALLOWED_VIDEO_EXTENSIONS)


def validate_video_size(file_obj, max_mb=50):
    """Reject uploaded videos larger than `max_mb` megabytes."""
    if file_obj and file_obj.size > max_mb * 1024 * 1024:
        raise ValidationError(f'Video too large. Maximum size is {max_mb} MB.')


MIN_ESTABLISHED_YEAR = 1900


def validate_established_year(value):
    """Accept a 4-digit establishment year between 1900 and the current year."""
    current_year = date.today().year
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(_('Enter a valid year (e.g. 2015).'))
    if value < MIN_ESTABLISHED_YEAR or value > current_year:
        raise ValidationError(
            _('Enter a year between %(min)s and %(max)s.')
            % {'min': MIN_ESTABLISHED_YEAR, 'max': current_year}
        )
