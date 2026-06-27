from django.contrib import admin
from .models import Review

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('clinic', 'patient', 'rating', 'created_at')
    search_fields = ('clinic__clinic_name', 'patient__full_name', 'description')
    list_filter = ('rating', 'created_at')
