from django.utils import timezone

def get_client_ip(request):
    """Return the client's IP address, considering X-Forwarded-For if present."""
    if not request:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    if xff:
        # X-Forwarded-For may contain multiple IPs
        return xff.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')
