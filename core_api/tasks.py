from celery import shared_task
from .services import IngestionService

@shared_task
def process_document_task(document_id):
    service = IngestionService()
    return service.process_document(document_id)
