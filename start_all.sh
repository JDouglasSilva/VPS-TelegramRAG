#!/bin/bash
set -e

echo "Iniciando todos os serviços (Web, Celery, Telegram Bot) no mesmo container..."

# 1. Aplicar migrações e coletar arquivos estáticos
python manage.py migrate --noinput
python manage.py collectstatic --noinput

# 2. Iniciar o Celery Worker em background
echo "-> Iniciando Celery Worker em background..."
celery -A telegram_rag_project worker -l INFO &

# 3. Iniciar o Bot do Telegram em background
echo "-> Iniciando o Telegram Bot em background..."
python manage.py run_bot &

# 4. Iniciar o Servidor Web Gunicorn em foreground (isso manterá o container vivo)
echo "-> Iniciando o Servidor Web Django (Gunicorn)..."
exec gunicorn telegram_rag_project.wsgi:application --bind 0.0.0.0:8000 --workers 3
