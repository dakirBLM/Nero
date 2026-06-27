from django.urls import path
from .views import LandingPageView, ChoicePageView, healthz, readyz

urlpatterns = [
    path('', LandingPageView.as_view(), name='landing_page'),
    path('choice_page', ChoicePageView.as_view(), name='choice_page'),
    path('healthz', healthz, name='healthz'),
    path('readyz', readyz, name='readyz'),
]
