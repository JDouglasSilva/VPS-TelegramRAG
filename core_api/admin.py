from django.contrib import admin
from .models import Organization, Member, Document, VectorEntry, ChatSession, ChatMessage

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin', 'created_at')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role')
    list_filter = ('organization', 'role')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'organization', 'status', 'created_at')
    list_filter = ('organization', 'status')
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'organization', 'created_at')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'timestamp')
    list_filter = ('sender',)
