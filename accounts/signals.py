import logging
from django.contrib.auth.signals import user_login_failed
from django.core.cache import cache
from django.dispatch import receiver
from django.utils import timezone
from .utils import get_client_ip
from .models import BlockedIPRecord

logger = logging.getLogger(__name__)

# Configuration
MAX_ATTEMPTS = 5
WINDOW_SECONDS = 10 * 60  # 10 minutes
BLOCK_SECONDS = 10 * 60   # block IP for 10 minutes


@receiver(user_login_failed)
def handle_login_failed(sender, credentials, request, **kwargs):
    ip = get_client_ip(request) if request is not None else None
    if not ip:
        return

    # Check if IP is permanently blocked
    try:
        ip_record = BlockedIPRecord.objects.get(ip_address=ip)
        if ip_record.is_permanently_blocked:
            logger.warning('Login attempt from permanently blocked IP %s', ip)
            return
    except BlockedIPRecord.DoesNotExist:
        ip_record = None

    key = f'failed_login:{ip}'
    blocked_key = f'blocked_ip:{ip}'

    # If already blocked, nothing to do
    if cache.get(blocked_key):
        logger.debug('Login attempt from already-blocked IP %s', ip)
        return

    # Increment attempts (initialize with WINDOW_SECONDS)
    attempts = (cache.get(key) or 0) + 1
    cache.set(key, attempts, timeout=WINDOW_SECONDS)

    logger.debug('Failed login attempt %s for IP %s', attempts, ip)

    if attempts >= MAX_ATTEMPTS:
        # Store expiry timestamp as value so middleware/template can show remaining time
        expiry_ts = timezone.now().timestamp() + BLOCK_SECONDS
        cache.set(blocked_key, expiry_ts, timeout=BLOCK_SECONDS)
        cache.delete(key)
        logger.warning('IP %s blocked for %s seconds after %s failed attempts', ip, BLOCK_SECONDS, attempts)
        
        # Record persistent block
        if ip_record is None:
            ip_record = BlockedIPRecord.objects.create(ip_address=ip, block_count=1)
            logger.info('Created new BlockedIPRecord for %s (1st block)', ip)
        else:
            is_permanent = ip_record.increment_block_count()
            if is_permanent:
                logger.critical('IP %s PERMANENTLY BLOCKED after %s blocks', ip, ip_record.block_count)
                # Set longer cache block for permanent blocks
                cache.set(blocked_key, timezone.now().timestamp() + (24 * 60 * 60), timeout=24 * 60 * 60)  # 24 hours
            else:
                logger.warning('IP %s blocked %s times (permanent block at 3)', ip, ip_record.block_count)
