from django.contrib import admin
from django.utils import timezone
from .models import ChatRoom


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ("id", "user1", "user2", "is_messaging_blocked", "unlocked_at", "created_at")
    list_filter = ("is_messaging_blocked", "created_at", "unlocked_at")
    search_fields = ("user1__username", "user2__username")
    readonly_fields = ("created_at",)

    def save_model(self, request, obj, form, change):
        if obj.is_messaging_blocked:
            obj.unlocked_at = None
        elif obj.unlocked_at is None:
            obj.unlocked_at = timezone.now()
        super().save_model(request, obj, form, change)
