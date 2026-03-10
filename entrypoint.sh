#!/bin/bash
set -e

# Esperar banco de dados subir (prática recomendada, embora as vezes db suba rápido)
sleep 5

if [ "$1" = 'web' ]; then
    echo "Aplicando migrações..."
    python manage.py migrate --noinput

    echo "Coletando static files..."
    python manage.py collectstatic --noinput

    echo "Iniciando servidor web Gunicorn..."
    exec gunicorn telegram_rag_project.wsgi:application --bind 0.0.0.0:8000 --workers 3

elif [ "$1" = 'bot' ]; then
    echo "Iniciando o bot do Telegram..."
    exec python manage.py run_bot

elif [ "$1" = 'celery' ]; then
    echo "Iniciando worker do Celery..."
    exec celery -A telegram_rag_project worker -l INFO

elif [ "$1" = 'all' ]; then
    echo "Iniciando todos os serviços (Web + Bot + Celery)..."
    exec bash /app/start_all.sh

else
    echo "Comando não reconhecido. Use: web, bot, celery ou all."
    exec "$@"
fi
