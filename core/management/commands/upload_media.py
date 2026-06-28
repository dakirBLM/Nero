"""Upload local MEDIA_ROOT files to the configured S3/Supabase bucket.

Uploads each file at its EXACT relative key (e.g. clinic_posts/x.jpg) so the
paths stored in the database resolve. PHI directories (encrypted medical files)
are skipped — they need a separate decrypt-and-reupload step.

Usage (run locally with your Supabase S3 creds in the environment):
    USE_S3_MEDIA=1 S3_BUCKET=... S3_ENDPOINT_URL=... S3_ACCESS_KEY_ID=... \
    S3_SECRET_ACCESS_KEY=... S3_REGION=... S3_ADDRESSING_STYLE=path \
    python manage.py upload_media --dry-run
Then run again without --dry-run to actually upload.
"""
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

# PHI / encrypted — never bulk-upload these to the media bucket.
EXCLUDE_TOP_DIRS = {"medical_reports", "movement_videos"}


class Command(BaseCommand):
    help = "Upload local media/ files to the configured S3/Supabase bucket (excludes PHI)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List files without uploading.")
        parser.add_argument("--overwrite", action="store_true", help="Re-upload files even if present.")

    def handle(self, *args, **opts):
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError
        except ImportError:
            raise CommandError("boto3 is required: pip install boto3")

        opt = (settings.STORAGES.get("default", {}) or {}).get("OPTIONS", {}) or {}
        bucket = opt.get("bucket_name") or os.environ.get("S3_BUCKET")
        endpoint = opt.get("endpoint_url") or os.environ.get("S3_ENDPOINT_URL")
        access = opt.get("access_key") or os.environ.get("S3_ACCESS_KEY_ID")
        secret = opt.get("secret_key") or os.environ.get("S3_SECRET_ACCESS_KEY")
        region = opt.get("region_name") or os.environ.get("S3_REGION", "auto")
        addressing = os.environ.get("S3_ADDRESSING_STYLE", "path")

        if not (bucket and endpoint and access and secret):
            raise CommandError(
                "Object storage is not configured. Set USE_S3_MEDIA=1 and the S3_* env vars "
                "(S3_BUCKET, S3_ENDPOINT_URL, S3_ACCESS_KEY_ID, S3_SECRET_ACCESS_KEY)."
            )

        s3 = boto3.client(
            "s3", endpoint_url=endpoint, aws_access_key_id=access, aws_secret_access_key=secret,
            region_name=region,
            config=Config(signature_version="s3v4", s3={"addressing_style": addressing}),
        )

        media_root = Path(settings.MEDIA_ROOT)
        if not media_root.exists():
            raise CommandError(f"MEDIA_ROOT does not exist: {media_root}")

        uploaded = skipped = excluded = 0
        for path in sorted(media_root.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(media_root)
            if rel.parts and rel.parts[0] in EXCLUDE_TOP_DIRS:
                excluded += 1
                continue
            if path.name == ".DS_Store":
                continue
            key = str(rel).replace(os.sep, "/")

            if not opts["overwrite"] and not opts["dry_run"]:
                try:
                    s3.head_object(Bucket=bucket, Key=key)
                    self.stdout.write(f"exists, skip  {key}")
                    skipped += 1
                    continue
                except ClientError:
                    pass

            if opts["dry_run"]:
                self.stdout.write(f"would upload  {key}")
            else:
                s3.upload_file(str(path), bucket, key)
                self.stdout.write(f"uploaded      {key}")
            uploaded += 1

        verb = "would upload" if opts["dry_run"] else "uploaded"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {uploaded} file(s); skipped {skipped} existing; excluded {excluded} PHI file(s)."
        ))
