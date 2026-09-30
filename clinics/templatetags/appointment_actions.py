from django import template
from django.urls import reverse

register = template.Library()


@register.simple_tag(takes_context=True)
def action_url(context, name, appointment_id):
    """URL for an appointment action in clinic or agency mode."""
    if context.get('agency_mode'):
        return reverse(f'agency_{name}', args=[context['clinic'].id, appointment_id])
    return reverse(name, args=[appointment_id])
