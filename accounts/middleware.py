from django.http import HttpResponseForbidden
from django.conf import settings
from django.core.cache import cache
from .utils import get_client_ip
from .models import BlockedIPRecord
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class BlockBlockedIPMiddleware:
    """Middleware to mark requests from blocked IPs and prevent login POSTs.

    - Sets `request.blocked_ip_until` to expiry timestamp (float) when IP is blocked.
    - Allows GET to the login page so the template can display a message.
    - Blocks POST attempts to the login path with 403.
    - Checks for permanently blocked IPs in database.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.login_path = getattr(settings, 'LOGIN_URL', '/accounts/login/')

    def __call__(self, request):
        ip = get_client_ip(request)
        if ip:
            # Check permanent blocks first
            try:
                ip_record = BlockedIPRecord.objects.get(ip_address=ip, is_permanently_blocked=True)
                logger.warning('Request from permanently blocked IP %s', ip)
                request.blocked_ip_until = timezone.now().timestamp() + (24 * 60 * 60)  # 24 hours
                request.blocked_remaining = 24 * 60 * 60  # Show as blocked for 24 hours
                request.is_permanently_blocked = True
                
                # Block all login attempts from permanently blocked IPs
                if (request.path == self.login_path or request.path.startswith(self.login_path)) and request.method == 'POST':
                    logger.warning('Blocking login POST from permanently blocked IP %s', ip)
                    return HttpResponseForbidden('This IP address has been permanently blocked due to repeated security violations.')
                    
            except BlockedIPRecord.DoesNotExist:
                pass
            
            # Check temporary blocks
            blocked_key = f'blocked_ip:{ip}'
            expiry_ts = cache.get(blocked_key)
            if expiry_ts:
                try:
                    expiry = float(expiry_ts)
                except Exception:
                    expiry = expiry_ts
                # remaining seconds until unblock
                try:
                    remaining = int(max(0, expiry - timezone.now().timestamp()))
                except Exception:
                    remaining = None
                request.blocked_ip_until = expiry
                request.blocked_remaining = remaining

                # If this is a login POST, block it
                if request.path == self.login_path or request.path.startswith(self.login_path):
                    if request.method == 'POST':
                        logger.info('Blocking login POST from temporarily blocked IP %s', ip)
                        return HttpResponseForbidden('Too many failed login attempts. Try again later.')
                    # allow GET so template can show a message

        return self.get_response(request)
