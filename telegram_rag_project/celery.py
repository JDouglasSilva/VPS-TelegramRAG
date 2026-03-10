import os
from celery import Celery

# Setup da variável de ambiente padrão do Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'telegram_rag_project.settings')

app = Celery('telegram_rag_project')

# Puxar config do django namespace CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Procurar arquivos tasks.py nos apps
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
