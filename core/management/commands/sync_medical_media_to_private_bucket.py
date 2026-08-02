from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from patients.models import MedicalRecord, MedicalRecordReport, MedicalRecordVideo
from patients.storage import get_medical_file_storage


class Command(BaseCommand):
    help = "Copy existing medical reports and movement videos from local storage to the private PHI bucket."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="List files without uploading.")
        parser.add_argument("--overwrite", action="store_true", help="Re-upload files even if present in the bucket.")

    def handle(self, *args, **opts):
        storage = get_medical_file_storage()
        remote = storage._get_remote_storage()
        if not remote:
            raise CommandError(
                "Private PHI object storage is not configured. Set PHI_S3_BUCKET, PHI_S3_ENDPOINT_URL, "
                "PHI_S3_ACCESS_KEY_ID, and PHI_S3_SECRET_ACCESS_KEY first."
            )

        seen = set()
        uploaded = 0
        skipped = 0
        missing = 0

        def sync_name(name):
            nonlocal uploaded, skipped, missing
            if not name or name in seen:
                return
            seen.add(name)

            try:
                if not opts["overwrite"] and remote.exists(name):
                    self.stdout.write(f"exists, skip  {name}")
                    skipped += 1
                    return
            except Exception:
                pass

            try:
                with storage.open(name, "rb") as f:
                    data = f.read()
            except Exception:
                self.stdout.write(self.style.WARNING(f"missing      {name}"))
                missing += 1
                return

            if opts["dry_run"]:
                self.stdout.write(f"would upload  {name}")
            else:
                remote._save(name, ContentFile(data))
                self.stdout.write(f"uploaded      {name}")
            uploaded += 1

        for record in MedicalRecord.objects.all().only("medical_reports", "patient_movement_video"):
            sync_name(getattr(record.medical_reports, "name", ""))
            sync_name(getattr(record.patient_movement_video, "name", ""))

        for report in MedicalRecordReport.objects.all().only("file"):
            sync_name(getattr(report.file, "name", ""))

        for video in MedicalRecordVideo.objects.all().only("file"):
            sync_name(getattr(video.file, "name", ""))

        verb = "would upload" if opts["dry_run"] else "uploaded"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {uploaded} file(s); skipped {skipped} existing; missing {missing}."
        ))
