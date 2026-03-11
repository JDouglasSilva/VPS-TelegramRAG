from rest_framework import viewsets, status, parsers
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import ChatSession, ChatMessage, Organization, Document, KnowledgeBase
from .serializers import ChatSessionSerializer, ChatMessageSerializer, DocumentSerializer
from .services import ChatService

class ChatViewSet(viewsets.ModelViewSet):
    serializer_class = ChatSessionSerializer
    
    def get_queryset(self):
        # Apenas as sessões do usuário atual
        return ChatSession.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        kb_id = request.data.get('knowledge_base')
        if not kb_id:
            return Response({'error': 'Necessário informar knowledge_base'}, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            kb = KnowledgeBase.objects.get(id=kb_id)
        except KnowledgeBase.DoesNotExist:
            return Response({'error': 'KnowledgeBase não encontrada'}, status=status.HTTP_404_NOT_FOUND)

        session = ChatSession.objects.create(
            user=request.user if request.user.is_authenticated else None,
            knowledge_base=kb,
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
        # Apenas documentos da org atual do user (para o upload modal)
        member = self.request.user.membership
        return Document.objects.filter(knowledge_base__organization=member.organization)

    def perform_create(self, serializer):
        kb_id = self.request.data.get('knowledge_base')
        kb = KnowledgeBase.objects.get(id=kb_id)
        
        serializer.save(
            uploader=self.request.user,
            knowledge_base=kb,
            filename=self.request.FILES['file'].name
        )
