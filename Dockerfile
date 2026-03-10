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
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copia e instala as dependências padrão
COPY requirements.txt requirements-local-ai.txt /app/
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código para o container
COPY . /app/

# Copia o arquivo de configuração do Supervisor
COPY supervisord.conf /app/supervisord.conf

# Porta que o web app vai escutar
EXPOSE 8000

CMD ["/usr/bin/supervisord", "-c", "/app/supervisord.conf"]
