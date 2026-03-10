from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ChatViewSet, DocumentViewSet

router = DefaultRouter()
router.register(r'chats', ChatViewSet, basename='chat')
router.register(r'documents', DocumentViewSet, basename='document')

urlpatterns = [
    path('', include(router.urls)),
]
