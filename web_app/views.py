from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from core_api.models import Member

def login_view(request):
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            return redirect('chat')
        return render(request, 'web_app/login.html', {'error': 'Credenciais inválidas'})
    return render(request, 'web_app/login.html')

@login_required
def chat_view(request):
    # Garantir que o usuário é membro de alguma org
    try:
        member = request.user.membership
    except Member.DoesNotExist:
        return render(request, 'web_app/chat.html', {'error': 'Você não pertence a nenhuma organização.'})
    
    return render(request, 'web_app/chat.html')
