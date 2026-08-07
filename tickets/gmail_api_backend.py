"""
Email backend Django yang ngirim lewat Gmail API (HTTPS), BUKAN SMTP.
"""

import base64
import logging

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class GmailAPIBackend(BaseEmailBackend):
    """Kirim EmailMessage Django lewat Gmail API alih-alih SMTP."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently, **kwargs)
        self._service = None

    def _get_service(self):
        if self._service is not None:
            return self._service

        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = Credentials(
            token=None,
            refresh_token=settings.GMAIL_REFRESH_TOKEN,
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET,
            token_uri='https://oauth2.googleapis.com/token',
            scopes=['https://www.googleapis.com/auth/gmail.send'],
        )
        self._service = build('gmail', 'v1', credentials=creds, cache_discovery=False)
        return self._service

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        try:
            service = self._get_service()
        except Exception:
            logger.exception("Gagal inisialisasi Gmail API service")
            if self.fail_silently:
                return 0
            raise

        sent_count = 0
        for message in email_messages:
            try:
                mime_message = message.message()
                raw = base64.urlsafe_b64encode(mime_message.as_bytes()).decode('ascii')
                service.users().messages().send(
                    userId='me',
                    body={'raw': raw},
                ).execute()
                sent_count += 1
            except Exception:
                logger.exception("Gagal kirim email lewat Gmail API ke %s", message.to)
                if not self.fail_silently:
                    raise

        return sent_count