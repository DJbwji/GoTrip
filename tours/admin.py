from django.contrib import admin
from .models import Destination, Category, Excursion, Departure, TourPhoto, Review

@admin.register(Destination)
class DestinationAdmin(admin.ModelAdmin):
    list_display = ['name','subtitle']
    search_fields = ['name']
    list_filter = ['name']
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name']
    search_fields = ['name']
    list_filter = ['name']
@admin.register(Excursion)
class ExcursionAdmin(admin.ModelAdmin):
    list_display = ['title','guide','destination','price','status','created_at']
    search_fields = ['title','description','guide__email']
    list_filter = ['status','destination','categories','created_at']
    readonly_fields = [f.name for f in Excursion._meta.fields] + ['categories','favorites']
    def has_add_permission(self, request): return False
@admin.register(Departure)
class DepartureAdmin(admin.ModelAdmin):
    list_display = ['excursion','date','capacity','reserved']
    search_fields = ['excursion__title']
    list_filter = ['date']
    readonly_fields = ['excursion','date','capacity','reserved']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
@admin.register(TourPhoto)
class TourPhotoAdmin(admin.ModelAdmin):
    list_display = ['excursion','image']
    search_fields = ['excursion__title']
    list_filter = ['excursion__destination']
    readonly_fields = ['excursion','image']
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['excursion','user','rating','created_at']
    search_fields = ['text','user__email','excursion__title']
    list_filter = ['rating','created_at']
    readonly_fields = ['excursion','user','rating','text','created_at']
    def has_add_permission(self, request): return False
