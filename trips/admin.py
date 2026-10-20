from django.contrib import admin
from .models import Trip

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ['title','organizer','destination','start_date','end_date','capacity']
    search_fields = ['title','description','organizer__email']
    list_filter = ['destination','start_date']
    readonly_fields = [f.name for f in Trip._meta.fields] + ['participants']
    def has_add_permission(self, request): return False
