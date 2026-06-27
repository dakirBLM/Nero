from django.views.generic import TemplateView
from django.http import JsonResponse, HttpResponse
from django.db import connection


class LandingPageView(TemplateView):
    template_name = 'landing_page.html'


class ChoicePageView(TemplateView):
    template_name = 'choice_page.html'


def healthz(request):
    """Liveness probe — the process is up. Fast, no DB hit."""
    return HttpResponse('ok', content_type='text/plain')


def readyz(request):
    """Readiness probe — can serve traffic (database reachable)."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
    except Exception:
        return JsonResponse({'status': 'unavailable'}, status=503)
    return JsonResponse({'status': 'ready'})
