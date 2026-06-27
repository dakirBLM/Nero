from django.contrib import admin
from .models import Post


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
	list_display = ("author", "created_at")
	search_fields = ("author__username", "clinic__clinic_name", "description")
	list_filter = ("created_at", "clinic")
