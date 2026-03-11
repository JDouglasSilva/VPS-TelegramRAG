from django.urls import path
from .views import chat_view, login_view, dashboard_view, create_kb_view

urlpatterns = [
    path('login/', login_view, name='login'),
    path('', chat_view, name='chat'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('dashboard/create_kb/', create_kb_view, name='create_kb'),
]
