import base64
import hashlib

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible


def _get_fernet():
    """Build a Fernet instance from settings.ENCRYPTION_KEY.

    ENCRYPTION_KEY must be a real Fernet key (Fernet.generate_key()) supplied via
    the environment. We only fall back to deriving a key from SECRET_KEY in local
    development (DEBUG=True); in production a missing ENCRYPTION_KEY is a hard error
    so PHI is never encrypted under a guessable, key-reuse value.
    """
    key = getattr(settings, 'ENCRYPTION_KEY', None)
    if not key:
        if getattr(settings, 'DEBUG', False):
            # Dev-only fallback so uploads work without extra setup.
            key = base64.urlsafe_b64encode(
                hashlib.sha256(settings.SECRET_KEY.encode()).digest()
            )
        else:
            raise RuntimeError(
                'ENCRYPTION_KEY environment variable is required to encrypt '
                'medical files. Generate one with: python -c '
                '"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"'
            )
    if isinstance(key, str):
        key = key.encode()
    return Fernet(key)


@deconstructible
class EncryptedFileSystemStorage(FileSystemStorage):
    """Local-disk Fernet-encrypted storage.

    Files are encrypted before saving and decrypted on read.
    .url(name) returns the Django secure-proxy URL so files are
    never directly accessible; the view decrypts before streaming.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fernet = None

    @property
    def fernet(self):
        # Built lazily: importing models, running migrations, and collectstatic
        # must NOT require ENCRYPTION_KEY — only actual file encrypt/decrypt does.
        if self._fernet is None:
            self._fernet = _get_fernet()
        return self._fernet

    def _save(self, name, content):
        content.seek(0)
        data = content.read()
        if not isinstance(data, bytes):
            data = data.encode()
        encrypted = ContentFile(self.fernet.encrypt(data))
        return super()._save(name, encrypted)

    def open(self, name, mode='rb'):
        f = super().open(name, mode)
        encrypted = f.read()
        try:
            data = self.fernet.decrypt(encrypted)
        finally:
            f.close()
        return ContentFile(data)

    def url(self, name):
        """Return the server-side decrypt proxy URL."""
        from django.urls import reverse
        return reverse('secure_encrypted_media', kwargs={'blob_name': name})
