from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Profile, GuideApplication

@admin.register(User)
class GoTripUserAdmin(UserAdmin):
    list_display = ['email','first_name','last_name','is_staff','is_active']
    search_fields = ['email','first_name','last_name','username']
    list_filter = ['is_staff','is_active','date_joined']

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user','city','interests']
    search_fields = ['user__email','city','interests']
    list_filter = ['city']

@admin.register(GuideApplication)
class GuideApplicationAdmin(admin.ModelAdmin):
    list_display = ['user','status','updated_at']
    search_fields = ['user__email','experience']
    list_filter = ['status','updated_at']
    readonly_fields = ['user','experience','phone','status','comment','updated_at']
    def has_add_permission(self, request): return False
