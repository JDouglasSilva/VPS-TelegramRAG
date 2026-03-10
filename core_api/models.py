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

class Document(models.Model):
    class Status(models.TextChoices):
        PROCESSING = 'PROCESSING', 'Processando'
        READY = 'READY', 'Pronto'
        ERROR = 'ERROR', 'Erro'

    file = models.FileField(upload_to='documents/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    uploader = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='documents')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PROCESSING)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename

@receiver(post_save, sender=Document)
def trigger_document_processing(sender, instance, created, **kwargs):
    if created:
        from .tasks import process_document_task
        process_document_task.delay(instance.id)
class VectorEntry(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='vectors')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='vectors')
    content = models.TextField()
    embedding = VectorField(dimensions=384)  # text-embedding-004 do Gemini tem 768 dimensões por padrão
    page_number = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['organization']),
        ]

class ChatSession(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    title = models.CharField(max_length=255, default="Novo Chat")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.user.username}"

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

