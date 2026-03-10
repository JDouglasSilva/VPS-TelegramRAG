from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ChatSession, ChatMessage, Organization, Document
from .serializers import ChatSessionSerializer, ChatMessageSerializer, DocumentSerializer
from .services import ChatService

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    
    def get_queryset(self):
        # Apenas as sessões do usuário atual
        return ChatSession.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        # Simplificação: Pega a primeira organização do usuário
        member = request.user.membership
        session = ChatSession.objects.create(
            user=request.user,
            organization=member.organization,
            title=request.data.get('title', 'Novo Chat')
        )
        serializer = self.get_serializer(session)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def ask(self, request, pk=None):
        session = self.get_object()
        query = request.data.get('query')
        
        if not query:
            return Response({'error': 'Campo query é obrigatório'}, status=status.HTTP_400_BAD_REQUEST)
        
        service = ChatService()
        bot_msg = service.generate_response(session.id, query)
        
        serializer = ChatMessageSerializer(bot_msg)
        return Response(serializer.data)

class DocumentViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentSerializer
    parser_classes = [parsers.MultiPartParser, parsers.FormParser]
    
    def get_queryset(self):
        member = self.request.user.membership
        return Document.objects.filter(organization=member.organization)

    def perform_create(self, serializer):
        member = self.request.user.membership
        serializer.save(
            uploader=self.request.user,
            organization=member.organization,
            filename=self.request.FILES['file'].name
        )
