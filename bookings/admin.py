from django.contrib import admin
from .models import Booking

@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['reference','user','departure','people','total','status','created_at']
    search_fields = ['reference','user__email','departure__excursion__title']
    list_filter = ['status','created_at']
    readonly_fields = [f.name for f in Booking._meta.fields]
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
