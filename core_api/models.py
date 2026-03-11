from django.db import models
from django.contrib.auth.models import User
from pgvector.django import VectorField
from django.db.models.signals import post_save
from django.dispatch import receiver
import uuid

class Organization(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    admin = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_organizations')

    def __str__(self):
        return self.name

class Member(models.Model):
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        CONTRIBUTOR = 'CONTRIBUTOR', 'Contribuidor'
        USER = 'USER', 'Usuário'

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='membership')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=Role.choices, default=Role.USER)
    
    telegram_id = models.BigIntegerField(null=True, blank=True, unique=True)
    linking_token = models.UUIDField(default=uuid.uuid4, editable=False)

    def __str__(self):
        return f"{self.user.username} - {self.organization.name} ({self.role})"

class KnowledgeBase(models.Model):
    class AccessLevel(models.TextChoices):
        PUBLIC = 'PUBLIC', 'Público (Qualquer visitante na internet)'
        INTERNAL = 'INTERNAL', 'Interno (Todos da mesma Organização)'
        PRIVATE = 'PRIVATE', 'Privado (Apenas eu e Administradores)'

    name = models.CharField(max_length=255)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='knowledge_bases')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_bases')
    access_level = models.CharField(max_length=20, choices=AccessLevel.choices, default=AccessLevel.INTERNAL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_access_level_display()})"

class Document(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processando'
        READY = 'READY', 'Pronto'
        ERROR = 'ERROR', 'Erro'

    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='documents')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

@receiver(post_save, sender=Document)
def trigger_document_processing(sender, instance, created, **kwargs):
    if created:
        from .tasks import process_document_task
        process_document_task.delay(instance.id)
import os
import environ
from django.conf import settings

env = environ.Env()
use_local = env.bool('USE_LOCAL_EMBEDDINGS', default=False)
VECTOR_DIMS = 384 if use_local else 768

class VectorEntry(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='vectors')
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='vectors')
    content = models.TextField()
    embedding = VectorField(dimensions=VECTOR_DIMS)
    page_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['knowledge_base']),
        ]

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    knowledge_base = models.ForeignKey(KnowledgeBase, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=255, default="Novo Chat")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        user_name = self.user.username if self.user else 'Guest'
        return f"{self.title} - {user_name} ({self.knowledge_base.name})"

class ChatMessage(models.Model):
    class Sender(models.TextChoices):
        USER = 'USER', 'Usuário'
        BOT = 'BOT', 'Bot'

    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    sender = models.CharField(max_length=10, choices=Sender.choices)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    # Armazena os IDs dos VectorEntry usados como contexto (para mostrar fonte depois)
    context_sources = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.sender}: {self.content[:30]}..."

