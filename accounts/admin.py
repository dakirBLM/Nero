from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, BlockedIPRecord
from django.utils.html import format_html

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'user_type', 'is_staff')
    list_filter = ('user_type', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('User Type', {'fields': ('user_type',)}),
    )


@admin.register(BlockedIPRecord) 
class BlockedIPRecordAdmin(admin.ModelAdmin):
    list_display = ('ip_address', 'block_count', 'status_display', 'first_blocked', 'last_blocked')
    list_filter = ('is_permanently_blocked', 'block_count', 'first_blocked', 'last_blocked')
    search_fields = ('ip_address', 'reason')
    readonly_fields = ('first_blocked', 'created_at', 'updated_at')
    ordering = ('-last_blocked',)
    
    fieldsets = (
        ('IP Information', {
            'fields': ('ip_address', 'block_count', 'is_permanently_blocked')
        }),
        ('Block Details', {
            'fields': ('reason', 'first_blocked', 'last_blocked')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def status_display(self, obj):
        if obj.is_permanently_blocked:
            return format_html('<span style="color: red; font-weight: bold;">PERMANENTLY BLOCKED</span>')
        elif obj.block_count >= 2:
            return format_html('<span style="color: orange; font-weight: bold;">WARNING ({})</span>', obj.block_count)
        else:
            return format_html('<span style="color: blue;">Monitored ({})</span>', obj.block_count)
    status_display.short_description = 'Status'
    
    actions = ['unblock_ips', 'permanently_block_ips']
    
    def unblock_ips(self, request, queryset):
        count = queryset.update(is_permanently_blocked=False, reason='Manually unblocked by admin')
        self.message_user(request, f'{count} IP(s) successfully unblocked.')
    unblock_ips.short_description = "Unblock selected IPs"
    
    def permanently_block_ips(self, request, queryset):
        count = queryset.update(is_permanently_blocked=True, reason='Manually blocked by admin')
        self.message_user(request, f'{count} IP(s) permanently blocked.')
    permanently_block_ips.short_description = "Permanently block selected IPs"