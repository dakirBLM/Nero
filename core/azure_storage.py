"""
Custom Azure Blob Storage backend for private media files.

Every call to .url() generates a short-lived SAS token so the blob
stays private but can be viewed in the browser for a limited time.

Credentials are read from environment variables — see settings.py.
"""

from datetime import datetime, timedelta, timezone

from azure.storage.blob import (
    BlobServiceClient,
    generate_blob_sas,
    BlobSasPermissions,
)
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.utils.deconstruct import deconstructible


@deconstructible
class AzurePrivateMediaStorage(Storage):
    """Read/write blobs in a *private* Azure container.

    • Uploads go straight to Azure.
    • .url(name) returns a time-limited signed URL (default 1 h).
    """

    def __init__(self):
        self.account_name = settings.AZURE_ACCOUNT_NAME
        self.account_key = settings.AZURE_ACCOUNT_KEY
        self.container = settings.AZURE_MEDIA_CONTAINER
        self.prefix = getattr(settings, "AZURE_MEDIA_PREFIX", "media")
        self.expiry_seconds = getattr(settings, "AZURE_SAS_EXPIRY_SECONDS", 3600)
        conn_str = (
            f"DefaultEndpointsProtocol=https;"
            f"AccountName={self.account_name};"
            f"AccountKey={self.account_key};"
            f"EndpointSuffix=core.windows.net"
        )
        self.client = BlobServiceClient.from_connection_string(conn_str)
        self.container_client = self.client.get_container_client(self.container)

    def _blob_name(self, name):
        """Prepend the prefix folder, e.g. 'media/patient_profile_pics/x.jpg'."""
        if self.prefix:
            return f"{self.prefix}/{name}"
        return name

    # ---------- write ----------
    def _save(self, name, content):
        content.seek(0)
        blob = self.container_client.get_blob_client(self._blob_name(name))
        blob.upload_blob(content.read(), overwrite=True)
        return name

    # ---------- read ----------
    def _open(self, name, mode="rb"):
        blob = self.container_client.get_blob_client(self._blob_name(name))
        data = blob.download_blob().readall()
        return ContentFile(data)

    # ---------- url with SAS ----------
    def url(self, name):
        """Return a signed URL valid for ``self.expiry_seconds``."""
        full_name = self._blob_name(name)
        sas = generate_blob_sas(
            account_name=self.account_name,
            container_name=self.container,
            blob_name=full_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=datetime.now(timezone.utc) + timedelta(seconds=self.expiry_seconds),
        )
        return (
            f"https://{self.account_name}.blob.core.windows.net/"
            f"{self.container}/{full_name}?{sas}"
        )

    # ---------- helpers ----------
    def exists(self, name):
        blob = self.container_client.get_blob_client(self._blob_name(name))
        try:
            blob.get_blob_properties()
            return True
        except Exception:
            return False

    def delete(self, name):
        blob = self.container_client.get_blob_client(self._blob_name(name))
        blob.delete_blob()

    def size(self, name):
        blob = self.container_client.get_blob_client(self._blob_name(name))
        props = blob.get_blob_properties()
        return props.size

    def listdir(self, path=""):
        full_path = self._blob_name(path) if path else (self.prefix or "")
        blobs = self.container_client.list_blobs(name_starts_with=full_path)
        files, dirs = [], set()
        for b in blobs:
            relative = b.name[len(path):].lstrip("/")
            parts = relative.split("/")
            if len(parts) > 1:
                dirs.add(parts[0])
            else:
                files.append(relative)
        return list(dirs), files
