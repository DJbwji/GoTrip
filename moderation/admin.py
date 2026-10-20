from django.contrib import admin
from .models import Complaint

@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = ['excursion','user','status','created_at']
    search_fields = ['text','excursion__title','user__email']
    list_filter = ['status','created_at']
    readonly_fields = [f.name for f in Complaint._meta.fields]
    def has_add_permission(self, request): return False
