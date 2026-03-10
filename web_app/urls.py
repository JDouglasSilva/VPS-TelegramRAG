from django.urls import path
from .views import chat_view, login_view

urlpatterns = [
    path('login/', login_view, name='login'),
    path('', chat_view, name='chat'),
]
