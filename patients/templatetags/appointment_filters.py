from django import template
from datetime import date

register = template.Library()

@register.filter
def filter_status(queryset, status):
    return queryset.filter(status=status)

@register.filter
def filter_upcoming(queryset):
    return queryset.filter(status='accepted', appointment_date__gte=date.today())