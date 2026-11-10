import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.instrumentos.models import Instrumento
from .forms import CadastroForm

Usuario = get_user_model()
logger = logging.getLogger(__name__)


def _enviar_email(assunto, mensagem, destinatarios):
    """Envia e-mail sem quebrar o fluxo caso o serviço de e-mail esteja indisponível."""
    if not destinatarios:
        return
    try:
        send_mail(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, destinatarios)
    except Exception:
        logger.exception('Falha ao enviar e-mail: %s', assunto)


def cadastro_view(request):
    """Auto-cadastro: a conta fica inativa (pendente) até um líder aprovar."""
    if request.user.is_authenticated:
        return redirect('home')

    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()

        lideres = list(
            Usuario.objects.filter(is_lider=True, is_active=True)
            .exclude(email='').values_list('email', flat=True)
        )
        link = request.build_absolute_uri(reverse('integrantes'))
        _enviar_email(
            'Novo cadastro aguardando aprovação - Louvor IPO',
            f'{usuario.get_full_name()} ({usuario.email}) se cadastrou no Louvor IPO '
            f'e está aguardando aprovação.\n\nAprove ou recuse em: {link}',
            lideres,
        )
        return render(request, 'cadastro_enviado.html', {'nome': usuario.first_name})

    return render(request, 'cadastro.html', {
        'form': form,
        'instrumentos': Instrumento.objects.all(),
        'selecionados': [str(i) for i in form['instrumentos'].value() or []],
    })


@login_required
@requer_lider
def integrantes_view(request):
    todos = Usuario.objects.all().order_by('first_name').prefetch_related('instrumentos')
    instrumentos = Instrumento.objects.all().order_by('nome')  # Para preencher o modal

    return render(request, 'integrantes.html', {
        'integrantes': [u for u in todos if u.is_active],
        'pendentes': [u for u in todos if not u.is_active],
        'instrumentos': instrumentos
    })


@login_required
@requer_lider
@require_POST
def aprovar_integrante(request, id):
    integrante = get_object_or_404(Usuario, id=id, is_active=False)
    integrante.is_active = True
    integrante.save(update_fields=['is_active'])
    messages.success(request, f'Cadastro de {integrante.get_full_name()} aprovado.')

    _enviar_email(
        'Cadastro aprovado - Louvor IPO',
        f'Olá, {integrante.first_name}!\n\nSeu cadastro no Louvor IPO foi aprovado. '
        f'Entre com seu e-mail e senha em: {request.build_absolute_uri(reverse("login"))}',
        [integrante.email],
    )
    return redirect('integrantes')


@login_required
@requer_lider
@require_POST
def recusar_integrante(request, id):
    integrante = get_object_or_404(Usuario, id=id, is_active=False)
    nome = integrante.get_full_name()
    integrante.delete()
    messages.success(request, f'Cadastro de {nome} recusado.')
    return redirect('integrantes')


@login_required
@requer_lider
def salvar_integrante(request):
    if request.method != "POST":
        return redirect('integrantes')

    id_usuario = request.POST.get('id')
    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    email = request.POST.get('email', '').strip().lower()
    instrumentos_ids = request.POST.getlist('instrumentos')
    is_lider = request.POST.get('is_lider') == 'on'

    duplicado = Usuario.objects.filter(email__iexact=email)
    if id_usuario:
        duplicado = duplicado.exclude(id=id_usuario)
    if duplicado.exists():
        messages.error(request, f'Já existe um integrante com o e-mail {email}.')
        return redirect('integrantes')

    if id_usuario:
        usuario = get_object_or_404(Usuario, id=id_usuario)
        # Mantém o username em sincronia quando ele era o próprio e-mail
        if usuario.username.lower() == (usuario.email or '').lower():
            usuario.username = email
        usuario.first_name = first_name
        usuario.last_name = last_name
        usuario.email = email
        # Um líder não pode remover a própria liderança (perderia o acesso)
        if usuario != request.user:
            usuario.is_lider = is_lider
        usuario.save()
        messages.success(request, f'{usuario.get_full_name()} atualizado(a).')
    else:
        # Para novos usuários, o username é o e-mail
        usuario = Usuario.objects.create_user(
            username=email,
            email=email,
            first_name=first_name,
            last_name=last_name,
            password='louvoripo',
            is_lider=is_lider,
        )
        messages.success(request, f'{usuario.get_full_name()} cadastrado(a). Senha inicial: louvoripo')

    usuario.instrumentos.set(instrumentos_ids)  # Atualiza o ManyToMany
    return redirect('integrantes')


@login_required
@requer_lider
@require_POST
def excluir_integrante(request, id):
    integrante = get_object_or_404(Usuario, id=id)
    if integrante == request.user:
        messages.error(request, 'Você não pode excluir a sua própria conta.')
    else:
        integrante.delete()
        messages.success(request, 'Integrante excluído.')
    return redirect('integrantes')
