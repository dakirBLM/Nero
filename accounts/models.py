from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('patient', 'Patient'),
        ('clinic', 'Clinic'),
    )
    
    user_type = models.CharField(
        max_length=10, 
        choices=USER_TYPE_CHOICES,
        default='patient'
    )
    def __str__(self):
        return f"{self.username} ({self.user_type})"


class BlockedIPRecord(models.Model):
    """Persistent tracking of IPs that have been blocked multiple times."""
    ip_address = models.GenericIPAddressField(unique=True)
    block_count = models.PositiveIntegerField(default=0, help_text="Number of times this IP has been blocked")
    first_blocked = models.DateTimeField(auto_now_add=True)
    last_blocked = models.DateTimeField(auto_now=True)
    is_permanently_blocked = models.BooleanField(default=False, help_text="IP is permanently blocked after 3+ blocks")
    reason = models.TextField(blank=True, help_text="Reason for permanent block")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-last_blocked']
        verbose_name = "Blocked IP Record"
        verbose_name_plural = "Blocked IP Records"

    def __str__(self):
        status = "PERMANENTLY BLOCKED" if self.is_permanently_blocked else f"Blocked {self.block_count} times"
        return f"{self.ip_address} - {status}"

    def increment_block_count(self):
        """Increment block count and check if IP should be permanently blocked."""
        self.block_count += 1
        self.last_blocked = timezone.now()
        
        # Permanently block after 3 blocks
        if self.block_count >= 3:
            self.is_permanently_blocked = True
            self.reason = f"IP blocked {self.block_count} times - automatic permanent block"
        
        self.save()
        return self.is_permanently_blocked