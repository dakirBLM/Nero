"""Email a clinic everything it can see about a patient's appointment.

Medical files are decrypted through the PHI storage and attached, up to the
provider's message size limit; anything that does not fit is listed instead.
"""
import logging
import mimetypes
import os
from dataclasses import dataclass, field

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from clinics.compatibility import medical_record_age
from patients.models import MedicalRecord

logger = logging.getLogger(__name__)

# Brevo's transactional API rejects the whole message (body + attachments) above
# 20 MB. Attachments are base64-encoded in that payload (~4/3), so this budget
# is the encoded size we will send and leaves room for the HTML and text bodies.
ATTACHMENT_BUDGET = 16 * 1024 * 1024

MOBILITY_AID_FIELDS = ('uses_wheelchair', 'uses_walker', 'uses_crutch')
GENERAL_CONDITION_FIELDS = (
    'bowel_control', 'urine_control', 'uses_permanent_catheter', 'uses_intermittent_catheter',
    'uses_medical_condom', 'uses_diapers', 'can_breathe_normally', 'can_eat_independently',
    'can_dress_independently', 'is_aware_and_cooperative', 'is_self_reliant',
    'uses_feeding_tube', 'uses_stool_tube', 'uses_urine_tube', 'uses_tracheostomy_tube',
)
MEDICAL_CONDITION_FIELDS = (
    'has_bedsores', 'has_diabetes', 'uses_insulin', 'has_heart_problems',
    'has_high_blood_pressure', 'has_infectious_diseases', 'has_vein_thrombosis', 'has_depression',
)


@dataclass
class SendResult:
    sent: bool = False
    attached: list = field(default_factory=list)
    skipped: list = field(default_factory=list)


def _yes_no(value):
    return 'Yes' if value else 'No'


def _label(field_name):
    return str(MedicalRecord._meta.get_field(field_name).verbose_name).capitalize()


def _flag_rows(record, field_names):
    return [(_label(name), _yes_no(getattr(record, name))) for name in field_names]


def record_sections(appointment):
    """Everything the clinic appointment page and medical-record page show."""
    record = appointment.medical_record
    patient = appointment.patient
    age = medical_record_age(record)
    return [
        ('Personal information', [
            ('Full name', f'{record.first_name} {record.last_name}'),
            ('Gender', record.get_gender_display()),
            ('Date of birth', record.date_of_birth),
            ('Age', age if age is not None else '-'),
            ('Country', record.country),
            ('Address', record.address),
            ('Email', record.email or patient.user.email or '-'),
            ('Mobile', record.mobile_number or patient.phone or '-'),
            ('WhatsApp', record.whatsapp_number or '-'),
        ]),
        ('Medical information', [
            ('Main diagnosis', record.main_diagnosis),
            ('Injury date', record.injury_date),
            ('Movement ability', record.get_movement_ability_display()),
            ('Height (cm)', record.height),
            ('Weight (kg)', record.weight),
            ('Current medications', record.current_medications or 'None'),
            ('Allergies', record.allergies or 'None'),
            ('Previous surgeries', record.previous_surgeries or 'None'),
        ]),
        ('Mobility aids', _flag_rows(record, MOBILITY_AID_FIELDS)),
        ('General patient condition', _flag_rows(record, GENERAL_CONDITION_FIELDS)),
        ('Medical conditions', _flag_rows(record, MEDICAL_CONDITION_FIELDS)),
        ('Booking request', [
            ('Status', appointment.get_status_display()),
            ('Requested service', appointment.requested_service or '-'),
            ('Needs accommodation', _yes_no(appointment.needs_accommodation)),
            ('Accommodation type', appointment.get_accommodation_type_display() or 'Not provided'),
            ('Companions', appointment.companions_count if appointment.companions_count is not None else 0),
            ('Treatment start', appointment.treatment_start_date or 'Not provided'),
            ('Treatment end', appointment.treatment_end_date or 'Not provided'),
            ('Appointment date', appointment.appointment_date or '-'),
            ('Patient notes', appointment.notes or '-'),
            ('Clinic proposal note', appointment.clinic_proposal_note or '-'),
            ('Patient reply', appointment.patient_response_note or '-'),
            ('Requested on', appointment.created_at),
        ]),
    ]


def _record_files(record):
    files = []
    if record.medical_reports:
        files.append(('Medical report', record.medical_reports))
    if record.patient_movement_video:
        files.append(('Movement video', record.patient_movement_video))
    files += [('Medical report', report.file) for report in record.reports.all()]
    files += [('Movement video', video.file) for video in record.videos.all()]
    return files


def _encoded_size(nbytes):
    """Bytes this payload occupies once base64-encoded into the JSON body."""
    return (nbytes + 2) // 3 * 4


def _stored_size(field_file):
    return field_file.size


def _read_decrypted(field_file):
    handle = field_file.open('rb')
    try:
        return handle.read()
    finally:
        handle.close()


def collect_attachments(record):
    """Return (attachments, skipped): decrypted files that fit the size budget.

    Size is checked before reading. storage.size() does not load the file; for
    PHI storage it is the ciphertext, which is at least as big as the decrypted
    bytes, so a file that is already over the budget is skipped unread. The
    check on the decrypted length stays, because a size at or under the budget
    can still encode to more than the budget.
    """
    attachments, skipped = [], []
    budget = ATTACHMENT_BUDGET
    for label, field_file in _record_files(record):
        name = os.path.basename(field_file.name)
        try:
            stored_size = _stored_size(field_file)
        except Exception:
            logger.exception('Could not stat medical file %s for record %s', name, record.pk)
            skipped.append((label, name, 'could not be read'))
            continue
        if stored_size > budget:
            skipped.append((label, name, 'too large to attach'))
            continue
        try:
            data = _read_decrypted(field_file)
        except Exception:
            logger.exception('Could not read medical file %s for record %s', name, record.pk)
            skipped.append((label, name, 'could not be read'))
            continue
        encoded = _encoded_size(len(data))
        if encoded > budget:
            skipped.append((label, name, 'too large to attach'))
            continue
        budget -= encoded
        mimetype = mimetypes.guess_type(name)[0] or 'application/octet-stream'
        attachments.append((name, data, mimetype))
    return attachments, skipped


def send_patient_details_email(appointment, to_email, base_url=''):
    record = appointment.medical_record
    clinic = appointment.clinic
    result = SendResult()

    attachments, result.skipped = collect_attachments(record)
    result.attached = [name for name, _data, _mimetype in attachments]

    context = {
        'appointment': appointment,
        'clinic': clinic,
        'patient': appointment.patient,
        'record': record,
        'sections': record_sections(appointment),
        'attached': result.attached,
        'skipped': result.skipped,
        'base_url': base_url,
    }
    subject = f'Patient details: {record.first_name} {record.last_name} — {clinic.clinic_name}'
    text_body = render_to_string('emails/patient_details.txt', context)
    html_body = render_to_string('emails/patient_details.html', context)

    message = EmailMultiAlternatives(subject, text_body, to=[to_email])
    message.attach_alternative(html_body, 'text/html')
    for name, data, mimetype in attachments:
        message.attach(name, data, mimetype)

    try:
        result.sent = bool(message.send(fail_silently=False))
    except Exception:
        logger.exception('Patient details email failed for appointment %s', appointment.pk)
    return result
