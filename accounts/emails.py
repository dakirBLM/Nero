"""Branded transactional emails (welcome, …).

Sending never raises: signup must succeed even if the mail provider is down.
"""
import logging
import os

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


def _base_url(request=None):
    # Deterministic order: Render's real hostname beats request headers (which
    # can be skewed by proxies), then the Sites framework, then the request.
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if host:
        return f'https://{host}'
    try:
        from django.contrib.sites.models import Site
        domain = Site.objects.get_current().domain
        if domain and 'example.com' not in domain:
            scheme = 'http' if domain.startswith(('localhost', '127.')) else 'https'
            return f'{scheme}://{domain}'
    except Exception:
        pass
    if request is not None:
        return request.build_absolute_uri('/').rstrip('/')
    return os.environ.get('SITE_BASE_URL', 'http://localhost:8000')


def send_welcome_email(user, request=None):
    """Send the branded welcome email to a newly registered user."""
    if not user.email:
        return False
    try:
        ctx = {
            'first_name': (user.first_name or user.username),
            'base_url': _base_url(request),
        }
        subject = _('Welcome to Nero! 🦫')
        text_body = render_to_string('emails/welcome.txt', ctx)
        html_body = render_to_string('emails/welcome.html', ctx)
        msg = EmailMultiAlternatives(subject, text_body, to=[user.email])
        msg.attach_alternative(html_body, 'text/html')
        sent = msg.send(fail_silently=False)
        logger.info('Welcome email sent=%s to user %s <%s>', sent, user.pk, user.email)
        return bool(sent)
    except Exception:
        logger.exception('Welcome email FAILED for user %s <%s>', user.pk, user.email)
        return False
