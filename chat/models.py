from django.db import models
from accounts.models import User

class ChatRoom(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_rooms_user1')
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_rooms_user2')
    created_at = models.DateTimeField(auto_now_add=True)
    is_messaging_blocked = models.BooleanField(
        default=True,
        help_text="Blocked by default. Admin unlocks this room after payment verification.",
    )
    unlocked_at = models.DateTimeField(null=True, blank=True)

    @property
    def is_patient_to_patient(self):
        return hasattr(self.user1, 'patient') and hasattr(self.user2, 'patient')

    @property
    def is_patient_to_clinic(self):
        user1_is_patient = hasattr(self.user1, 'patient')
        user2_is_patient = hasattr(self.user2, 'patient')
        user1_is_clinic = hasattr(self.user1, 'clinic')
        user2_is_clinic = hasattr(self.user2, 'clinic')
        return (user1_is_patient and user2_is_clinic) or (user2_is_patient and user1_is_clinic)

    @property
    def is_clinic_to_clinic(self):
        return hasattr(self.user1, 'clinic') and hasattr(self.user2, 'clinic')

    def has_payed_appointment(self):
        """Return True when this room links a patient and clinic with at least one payed appointment."""
        if not self.is_patient_to_clinic:
            return False

        from clinics.models import Appointment

        patient_obj = self.user1.patient if hasattr(self.user1, 'patient') else self.user2.patient
        clinic_obj = self.user1.clinic if hasattr(self.user1, 'clinic') else self.user2.clinic
        return Appointment.objects.filter(patient=patient_obj, clinic=clinic_obj, status='payed').exists()

    def has_upcoming_or_active_appointment(self):
        """Return True when this room links a patient and clinic with at least one upcoming or active appointment."""
        if not self.is_patient_to_clinic:
            return False

        from clinics.models import Appointment

        patient_obj = self.user1.patient if hasattr(self.user1, 'patient') else self.user2.patient
        clinic_obj = self.user1.clinic if hasattr(self.user1, 'clinic') else self.user2.clinic

        # Allow chat for paid or upcoming appointments
        active_statuses = ['paid', 'upcoming']
        return Appointment.objects.filter(
            patient=patient_obj,
            clinic=clinic_obj,
            status__in=active_statuses
        ).exists()

    @property
    def is_messaging_blocked_effective(self):
        # Patient-patient chats are always open, even if legacy rows were blocked.
        if self.is_patient_to_patient:
            return False

        # Clinic-clinic chats are always open, even if legacy rows were blocked.
        if self.is_clinic_to_clinic:
            return False

        # Patient-clinic chats are open when there is a paid or upcoming appointment.
        if self.is_patient_to_clinic:
            return not self.has_upcoming_or_active_appointment()

        # Keep original DB-driven behavior for other room types.
        return self.is_messaging_blocked

    def __str__(self):
        return f"ChatRoom: {self.user1.username} & {self.user2.username}"

    class Meta:
        unique_together = ('user1', 'user2')

class Message(models.Model):
    chat_room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        indexes = [
            # Speeds up the unread-count query: filter(chat_room=..., is_read=False)
            models.Index(fields=['chat_room', 'is_read']),
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        return f"Message from {self.sender.username} at {self.timestamp}"