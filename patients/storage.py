import base64
import hashlib
import os

from cryptography.fernet import Fernet
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage
from django.core.exceptions import ImproperlyConfigured
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


@deconstructible
class PrivateMedicalObjectStorage(Storage):
    """Store PHI in a private S3-compatible bucket with signed URLs.

    New uploads go to object storage when PHI_S3_* credentials are configured.
    Existing encrypted local files keep working through the fallback storage so
    we can migrate records gradually without breaking old URLs.
    """

    def __init__(self):
        self.local_storage = EncryptedFileSystemStorage()
        self._remote_storage = None
        self._remote_enabled = False

        bucket = os.environ.get('PHI_S3_BUCKET') or os.environ.get('S3_BUCKET')
        endpoint = os.environ.get('PHI_S3_ENDPOINT_URL') or os.environ.get('S3_ENDPOINT_URL')
        access_key = os.environ.get('PHI_S3_ACCESS_KEY_ID') or os.environ.get('S3_ACCESS_KEY_ID')
        secret_key = os.environ.get('PHI_S3_SECRET_ACCESS_KEY') or os.environ.get('S3_SECRET_ACCESS_KEY')

        if bucket and endpoint and access_key and secret_key:
            self._remote_enabled = True
            self._remote_config = {
                'bucket_name': bucket,
                'endpoint_url': endpoint,
                'access_key': access_key,
                'secret_key': secret_key,
                'region_name': os.environ.get('PHI_S3_REGION') or os.environ.get('S3_REGION', 'auto'),
                'addressing_style': os.environ.get('PHI_S3_ADDRESSING_STYLE') or os.environ.get('S3_ADDRESSING_STYLE', 'path'),
            }

    def _get_remote_storage(self):
        if not self._remote_enabled:
            return None
        if self._remote_storage is None:
            try:
                from storages.backends.s3 import S3Storage
            except ImportError as exc:
                raise ImproperlyConfigured('django-storages is required for PHI_S3_* uploads.') from exc

            opts = {
                'bucket_name': self._remote_config['bucket_name'],
                'endpoint_url': self._remote_config['endpoint_url'],
                'access_key': self._remote_config['access_key'],
                'secret_key': self._remote_config['secret_key'],
                'region_name': self._remote_config['region_name'],
                'signature_version': 's3v4',
                'addressing_style': self._remote_config['addressing_style'],
                'querystring_auth': True,
                'querystring_expire': 900,
                'default_acl': None,
                'file_overwrite': False,
            }
            self._remote_storage = S3Storage(**opts)
        return self._remote_storage

    def _remote_exists(self, name):
        remote = self._get_remote_storage()
        if not remote:
            return False
        try:
            return remote.exists(name)
        except Exception:
            return False

    def _preferred_storage(self, name=None):
        remote = self._get_remote_storage()
        if remote and (name is None or self._remote_exists(name)):
            return remote
        return self.local_storage

    def _save(self, name, content):
        remote = self._get_remote_storage()
        if remote:
            content.seek(0)
            return remote._save(name, content)
        return self.local_storage._save(name, content)

    def open(self, name, mode='rb'):
        storage = self._preferred_storage(name)
        return storage.open(name, mode)

    def url(self, name):
        storage = self._preferred_storage(name)
        return storage.url(name)

    def exists(self, name):
        remote = self._get_remote_storage()
        if remote and self._remote_exists(name):
            return True
        return self.local_storage.exists(name)

    def delete(self, name):
        remote = self._get_remote_storage()
        if remote and self._remote_exists(name):
            return remote.delete(name)
        return self.local_storage.delete(name)

    def size(self, name):
        storage = self._preferred_storage(name)
        return storage.size(name)

    def listdir(self, path=''):
        remote = self._get_remote_storage()
        if remote:
            try:
                return remote.listdir(path)
            except Exception:
                pass
        return self.local_storage.listdir(path)


def get_medical_file_storage():
    """Return the PHI storage backend.

    Uses private S3/Supabase object storage when the PHI_S3_* environment
    variables are configured; otherwise falls back to the existing encrypted
    local filesystem storage.
    """
    return PrivateMedicalObjectStorage()
