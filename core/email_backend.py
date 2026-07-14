"""Brevo (Sendinblue) HTTP API email backend.

Sends via https://api.brevo.com — plain HTTPS on port 443 — so it works from
hosts where outbound SMTP ports are blocked or flaky (e.g. some PaaS networks).
Activated automatically when BREVO_API_KEY is set (see settings.py).
"""
import json
import logging
from email.utils import parseaddr
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

API_URL = 'https://api.brevo.com/v3/smtp/email'


class BrevoAPIBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        api_key = getattr(settings, 'BREVO_API_KEY', '')
        if not api_key:
            if not self.fail_silently:
                raise RuntimeError('BREVO_API_KEY is not configured')
            return 0

        sent = 0
        for message in email_messages:
            try:
                name, email = parseaddr(message.from_email or settings.DEFAULT_FROM_EMAIL)
                payload = {
                    'sender': {'email': email, **({'name': name} if name else {})},
                    'to': [{'email': r} for r in message.recipients()],
                    'subject': message.subject,
                    'textContent': message.body or ' ',
                }
                for alt, mimetype in getattr(message, 'alternatives', []):
                    if mimetype == 'text/html':
                        payload['htmlContent'] = alt
                req = Request(
                    API_URL,
                    data=json.dumps(payload).encode('utf-8'),
                    headers={
                        'api-key': api_key,
                        'Content-Type': 'application/json',
                        'Accept': 'application/json',
                    },
                    method='POST',
                )
                with urlopen(req, timeout=15) as resp:
                    resp.read()
                sent += 1
            except (HTTPError, URLError, OSError) as exc:
                detail = ''
                if isinstance(exc, HTTPError):
                    try:
                        detail = exc.read().decode('utf-8', 'replace')[:300]
                    except Exception:
                        pass
                logger.error('Brevo API send failed: %s %s', exc, detail)
                if not self.fail_silently:
                    raise
        return sent
