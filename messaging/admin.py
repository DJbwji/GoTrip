from django.contrib import admin
from .models import Conversation, Message

@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['tourist','guide','created_at']
    search_fields = ['tourist__email','guide__email']
    list_filter = ['created_at']
    readonly_fields = ['tourist','guide','created_at']
    def has_add_permission(self, request): return False
@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['sender','conversation','created_at']
    search_fields = ['text','sender__email']
    list_filter = ['created_at']
    readonly_fields = ['sender','conversation','text','created_at']
    def has_add_permission(self, request): return False
