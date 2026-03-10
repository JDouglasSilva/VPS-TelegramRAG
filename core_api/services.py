import fitz  # PyMuPDF
import google.generativeai as genai
import os
import environ
from django.conf import settings
from .models import Document, VectorEntry, Organization, ChatSession, ChatMessage
import time
class LocalEmbeddingService:
    _instance = None
    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            # Importa apenas aqui dentro para não explodir por falta de memória/disco na VPS base
            from sentence_transformers import SentenceTransformer
            import torch
            
            # Modelo robusto para português e rápido
            cls._model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
            if torch.cuda.is_available():
                cls._model = cls._model.to('cuda')
        return cls._model

    def embed(self, text):
        model = self.get_model()
        embedding = model.encode(text, convert_to_tensor=False)
        return embedding.tolist()

class GeminiEmbeddingService:
    def __init__(self):
        env = environ.Env()
        environ.Env.read_env(os.path.join(settings.BASE_DIR, '.env'), overwrite=True)
        self.api_key = env('GEMINI_API_KEY', default='SUA_CHAVE_AQUI')
        if self.api_key != 'SUA_CHAVE_AQUI':
            genai.configure(api_key=self.api_key)
            
    def embed(self, text):
        # Usando o modelo textual de embedding do Gemini
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        return result['embedding']

class IngestionService:
    def __init__(self):
        env = environ.Env()
        environ.Env.read_env(os.path.join(settings.BASE_DIR, '.env'), overwrite=True)
        self.api_key = env('GEMINI_API_KEY', default='SUA_CHAVE_AQUI')
        if self.api_key != 'SUA_CHAVE_AQUI':
            genai.configure(api_key=self.api_key)
            
        use_local = env.bool('USE_LOCAL_EMBEDDINGS', default=False)
        if use_local:
            self.embed_service = LocalEmbeddingService()
        else:
            self.embed_service = GeminiEmbeddingService()

    def extract_text_from_pdf(self, pdf_path):
        """Extrai texto e metadados de página de um PDF."""
        doc = fitz.open(pdf_path)
        pages_content = []
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text("text")
            if text.strip():
                pages_content.append({
                    "text": text,
                    "page_number": page_num + 1
                })
        return pages_content

    def chunk_text(self, text, chunk_size=1500, overlap=300):
        """Divide o texto em pedaços menores com sobreposição aumentada."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + chunk_size
            chunks.append(text[start:end])
            start += chunk_size - overlap
        return chunks

    def process_document(self, document_id):
        """Fluxo completo de processamento de um documento."""
        try:
            document = Document.objects.get(id=document_id)
            document.status = Document.Status.PROCESSING
            document.save()

            pages = self.extract_text_from_pdf(document.file.path)
            
            for page in pages:
                chunks = self.chunk_text(page["text"])
                for chunk_content in chunks:
                    # Gerar embedding LOCALMENTE
                    embedding = self.embed_service.embed(chunk_content)

                    # Salvar no banco vetorial
                    VectorEntry.objects.create(
                        document=document,
                        organization=document.organization,
                        content=chunk_content,
                        embedding=embedding,
                        page_number=page["page_number"]
                    )

            document.status = Document.Status.READY
            document.save()
            return True

        except Exception as e:
            if 'document' in locals():
                document.status = Document.Status.ERROR
                document.save()
            print(f"Erro no processamento do documento {document_id}: {str(e)}")
            raise e

class ChatService:
    def __init__(self):
        env = environ.Env()
        environ.Env.read_env(os.path.join(settings.BASE_DIR, '.env'), overwrite=True)
        self.api_key = env('GEMINI_API_KEY', default='SUA_CHAVE_AQUI')
        if self.api_key != 'SUA_CHAVE_AQUI':
            genai.configure(api_key=self.api_key)
        self.model_name_chat = "models/gemini-flash-latest"
        
        use_local = env.bool('USE_LOCAL_EMBEDDINGS', default=False)
        if use_local:
            self.embed_service = LocalEmbeddingService()
        else:
            self.embed_service = GeminiEmbeddingService()

    def get_query_embedding(self, query):
        return self.embed_service.embed(query)

    def retrieve_context(self, query_embedding, organization_id, top_k=12):
        from pgvector.django import CosineDistance
        
        # Aumentado para 1 service para pegar mais contexto
        results = VectorEntry.objects.filter(
            organization_id=organization_id
        ).annotate(
            distance=CosineDistance('embedding', query_embedding)
        ).order_by('distance')[:top_k]
        
        return results

    def generate_response(self, session_id, user_query):
        session = ChatSession.objects.get(id=session_id)
        
        # 1. Embedding da pergunta
        query_embedding = self.get_query_embedding(user_query)
        
        # 2. Busca de contexto
        context_chunks = self.retrieve_context(query_embedding, session.organization.id)
        
        # 3. Formatação do contexto e fontes
        context_text = "\n\n".join([f"--- Fonte: {c.document.filename} (Pag {c.page_number}) ---\n{c.content}" for c in context_chunks])
        context_ids = [c.id for c in context_chunks]
        
        # 4. Busca histórico recente (últimas 5 mensagens)
        history = ChatMessage.objects.filter(session=session).order_by('-timestamp')[:5]
        history_text = "\n".join([f"{m.sender}: {m.content}" for m in reversed(history)])

        # 5. Prompt Final - Instruções mais rigorosas
        prompt = f"""
        Você é um assistente de inteligência artificial altamente detalhista.
        Sua missão é responder à pergunta do usuário baseando-se EXCLUSIVAMENTE no CONTEXTO fornecido abaixo.

        REGRAS CRÍTICAS:
        1. Use HTML para formatação (ex: <b>negrito</b>, <i>itálico</i>). 
        2. NÃO use asteriscos (**) para negrito.
        3. Para listas, use caracteres simples como '•' ou '-' no início da linha.
        4. Se a informação (como datas, prazos ou valores) estiver presente no contexto, extraia-a com precisão.
        5. Informe sempre o nome do documento e a página.

        HISTÓRICO RECENTE:
        {history_text}

        CONTEXTO RECUPERADO DOS DOCUMENTOS:
        {context_text}

        PERGUNTA DO USUÁRIO:
        {user_query}

        RESPOSTA ANALÍTICA:
        """

        # 6. Chamar LLM ou Mock
        if self.api_key != 'SUA_CHAVE_AQUI':
            model = genai.GenerativeModel(self.model_name_chat)
            response = model.generate_content(prompt)
            answer = response.text
        else:
            answer = f"[MOCK RESPONSE] Baseado nos documentos de {session.organization.name}, encontrei informações sobre: " + ", ".join([c.document.filename for c in context_chunks])

        # 7. Salvar mensagens
        ChatMessage.objects.create(session=session, sender=ChatMessage.Sender.USER, content=user_query)
        bot_msg = ChatMessage.objects.create(
            session=session, 
            sender=ChatMessage.Sender.BOT, 
            content=answer,
            context_sources=context_ids
        )
        
        return bot_msg
