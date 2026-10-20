from django.contrib import admin
from .models import Activity

@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ['user','text','created_at']
    search_fields = ['text','user__email']
    list_filter = ['created_at']
    readonly_fields = ['user','text','created_at']
    def has_add_permission(self, request): return False

admin.site.site_header = 'GoTrip — управление платформой'
admin.site.site_title = 'GoTrip Admin'
admin.site.index_title = 'Данные и настройки'
