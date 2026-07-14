from django.urls import path
from django.contrib.auth import views as auth_views
from .views import CustomLoginView, custom_logout_view, dashboard_redirect_view, google_start_view

urlpatterns = [
    path('login/', CustomLoginView.as_view(), name='login'),
    path('google/start/<str:role>/', google_start_view, name='google_start'),
    path('logout/', custom_logout_view, name='logout'),
    path('dashboard/', dashboard_redirect_view, name='dashboard_redirect'),

    # Password reset (Django built-in flow, styled templates)
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='accounts/password_reset_email.txt',
        html_email_template_name='accounts/password_reset_email.html',
        subject_template_name='accounts/password_reset_subject.txt',
    ), name='password_reset'),
    path('password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html',
    ), name='password_reset_done'),
    path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html',
    ), name='password_reset_complete'),
]
