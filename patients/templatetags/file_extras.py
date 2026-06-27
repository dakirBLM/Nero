import os
from django import template

register = template.Library()


@register.filter(name='basename')
def basename(value):
    """Return the filename portion of a path."""
    try:
        return os.path.basename(value) if value else ''
    except Exception:
        return ''
