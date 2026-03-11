from django.contrib import admin
from .models import Organization, Member, Document, VectorEntry, ChatSession, ChatMessage, KnowledgeBase

@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin', 'created_at')

@admin.register(Member)
class MemberAdmin(admin.ModelAdmin):
    list_display = ('user', 'organization', 'role')
    list_filter = ('organization', 'role')

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('filename', 'knowledge_base', 'status', 'created_at')
    list_filter = ('knowledge_base', 'status')
@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'knowledge_base', 'created_at')

@admin.register(KnowledgeBase)
class KnowledgeBaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'access_level', 'created_by')
    list_filter = ('organization', 'access_level')

@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('session', 'sender', 'timestamp')
    list_filter = ('sender',)
