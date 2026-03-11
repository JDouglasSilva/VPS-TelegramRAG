from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from core_api.models import Member, KnowledgeBase
from django.db.models import Q

def login_view(request):
    print("Nova versão de teste implantada na ShardCloud!")
    if request.method == 'POST':
        u = request.POST.get('username')
        p = request.POST.get('password')
        user = authenticate(username=u, password=p)
        if user:
            login(request, user)
            return redirect('chat')
        return render(request, 'web_app/login.html', {'error': 'Credenciais inválidas'})
    return render(request, 'web_app/login.html')

def chat_view(request):
    if request.user.is_authenticated:
        try:
            member = request.user.membership
            kbs = KnowledgeBase.objects.filter(
                Q(organization=member.organization),
                Q(access_level__in=[KnowledgeBase.AccessLevel.PUBLIC, KnowledgeBase.AccessLevel.INTERNAL]) |
                Q(access_level=KnowledgeBase.AccessLevel.PRIVATE, created_by=request.user) |
                Q(organization__admin=request.user)
            ).distinct()
        except Member.DoesNotExist:
            kbs = KnowledgeBase.objects.filter(access_level=KnowledgeBase.AccessLevel.PUBLIC)
    else:
        # Visitante anônimo: só vê bases públicas
        kbs = KnowledgeBase.objects.filter(access_level=KnowledgeBase.AccessLevel.PUBLIC)

    return render(request, 'web_app/chat.html', {'knowledge_bases': kbs})


@login_required
def dashboard_view(request):
    # Superusers Django podem ver tudo, mesmo sem Member
    if request.user.is_superuser:
        from core_api.models import Organization
        kbs = KnowledgeBase.objects.all()
        members = Member.objects.all()
        org = Organization.objects.first()
        return render(request, 'web_app/dashboard.html', {
            'organization': org,
            'kbs': kbs,
            'members': members,
            'is_admin': True
        })

    try:
        member = request.user.membership
        if member.role == Member.Role.USER:
            return redirect('chat') # Users normais não têm admin
            
        kbs = KnowledgeBase.objects.filter(organization=member.organization)
        members = Member.objects.filter(organization=member.organization)
        
        return render(request, 'web_app/dashboard.html', {
            'organization': member.organization,
            'kbs': kbs,
            'members': members,
            'is_admin': member.role == Member.Role.ADMIN
        })
    except Member.DoesNotExist:
        return redirect('chat')

@login_required
def create_kb_view(request):
    try:
        member = request.user.membership
        if member.role == Member.Role.USER:
            return redirect('chat') # Apenas Admin/Contributor
            
        if request.method == 'POST':
            name = request.POST.get('name')
            access_level = request.POST.get('access_level')
            
            KnowledgeBase.objects.create(
                name=name,
                organization=member.organization,
                created_by=request.user,
                access_level=access_level
            )
            return redirect('dashboard')
            
    except Member.DoesNotExist:
        pass
    
    return redirect('dashboard')
