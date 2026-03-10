# Use uma imagem Python enxuta
FROM python:3.12-slim

# Evita gerar arquivos .pyc e permite ler os logs em tempo real
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Configura o diretório dentro do container
WORKDIR /app

# Instala dependências do sistema (necessário para pgvector/psycopg2 e compilados)
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências do Python
COPY requirements.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Pré-baixa o modelo do sentence-transformers (Opcional, mas excelente para acelerar a subida)
# Basta importar no contêiner durante o build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

# Copia o restante do código para o container
COPY . /app/

# Prepara os scripts de inicialização
COPY entrypoint.sh start_all.sh /app/
RUN chmod +x /app/entrypoint.sh /app/start_all.sh

# Porta que o web app vai escutar
EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
