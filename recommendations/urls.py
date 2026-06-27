from django.urls import path
import importlib

app_name = 'recommendations'

def _lazy(name):
    def _view(request, *args, **kwargs):
        views = importlib.import_module('recommendations.views')
        return getattr(views, name)(request, *args, **kwargs)
    return _view

urlpatterns = [
    path('questionnaire/', _lazy('questionnaire_view'), name='questionnaire'),
    path('result/', _lazy('recommendation_result_view'), name='recommendation_result'),
    path('send-requests/', _lazy('send_appointment_requests_view'), name='send_requests'),
]
