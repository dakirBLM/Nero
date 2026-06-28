from django.contrib import admin
from django.urls import path, include
import os
from django.conf import settings
from django.conf.urls.static import static
from patients.views import nero_ai_chat_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/social/', include('allauth.urls')),
    path('patients/', include('patients.urls')),
    path('clinics/', include('clinics.urls')),
    path('chat/', include('chat.urls')),
    path('recommendations/', include('recommendations.urls')),
    path('posts/', include('posts.urls')),
    path('reviews/', include('reviews.urls')),
    path('api/nero-ai/', nero_ai_chat_api, name='nero_ai_chat_api'),
]
# Serve user-uploaded media (NON-PHI images: profile pics, clinic photos, posts).
# Medical files are NOT served here — they go through an authenticated, encrypted
# proxy view. When object storage (S3/Supabase) is enabled, media is served from
# there and this route is simply unused.
_default_backend = settings.STORAGES.get('default', {}).get('BACKEND', '') if hasattr(settings, 'STORAGES') else ''
if 'FileSystemStorage' in _default_backend or settings.DEBUG or os.environ.get('SERVE_MEDIA') == '1':
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
if settings.DEBUG or os.environ.get('SERVE_STATIC') == '1':
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])