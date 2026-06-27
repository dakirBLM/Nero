from django.urls import path
from .views import CustomLoginView, custom_logout_view, dashboard_redirect_view, google_start_view

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('google/start/<str:role>/', google_start_view, name='google_start'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', dashboard_redirect_view, name='dashboard_redirect'),
]