import os

from django.conf import settings
from django.db import migrations


def set_site_domain(apps, schema_editor):
    """Point the active Site at the real deployment domain.

    Password-reset emails (and anything using the Sites framework) build their
    links from this record — the Django default is the placeholder
    'example.com'. On Render the real host arrives via RENDER_EXTERNAL_HOSTNAME;
    locally we leave whatever is configured (dev links print to console anyway).
    """
    host = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
    if not host:
        return
    Site = apps.get_model('sites', 'Site')
    site_id = getattr(settings, 'SITE_ID', 1)
    # Only touch the active Site: other rows may carry allauth SocialApp links,
    # and Site.domain is unique so blanket updates can collide.
    Site.objects.update_or_create(
        pk=site_id,
        defaults={'domain': host, 'name': 'Nero'},
    )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0002_blockediprecord'),
        ('sites', '0002_alter_domain_unique'),
    ]

    operations = [
        migrations.RunPython(set_site_domain, noop),
    ]
