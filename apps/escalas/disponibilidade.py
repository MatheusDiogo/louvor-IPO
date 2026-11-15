"""Indisponibilidade dos integrantes: cada um informa os dias em que não pode servir, com justificativa.

Prazo para informar um mês: a sexta-feira antes do último domingo do mês anterior.
Ex.: dezembro/2026 -> novembro termina no domingo 29 -> prazo sexta 27/11.
Na semana do prazo, todos recebem dois avisos: na segunda e na própria sexta (ver avisos.py).
"""
import calendar
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Escala, Indisponibilidade

MESES_A_FRENTE = 12  # até quantos meses à frente dá para informar


def _primeiro_dia(dia):
    return dia.replace(day=1)


def _somar_meses(mes, n):
    total = mes.year * 12 + (mes.month - 1) + n
    return date(total // 12, total % 12 + 1, 1)


def ultimo_domingo(ano, mes):
    ultimo = date(ano, mes, calendar.monthrange(ano, mes)[1])
    return ultimo - timedelta(days=(ultimo.weekday() - 6) % 7)  # weekday: segunda=0 ... domingo=6


def prazo_do_mes(mes):
    """Último dia para informar a indisponibilidade de `mes` (primeiro dia do mês)."""
    anterior = _somar_meses(mes, -1)
    return ultimo_domingo(anterior.year, anterior.month) - timedelta(days=2)


def aviso_segunda(mes):
    """Segunda-feira da semana do prazo (primeiro aviso)."""
    return prazo_do_mes(mes) - timedelta(days=4)


def mes_aberto(mes, hoje=None):
    hoje = hoje or timezone.localdate()
    return hoje <= prazo_do_mes(mes) and mes <= _somar_meses(_primeiro_dia(hoje), MESES_A_FRENTE)


def proximo_mes_aberto(hoje=None):
    """Primeiro mês que ainda dá para informar (normalmente o mês seguinte)."""
    hoje = hoje or timezone.localdate()
    mes = _somar_meses(_primeiro_dia(hoje), 1)
    while not mes_aberto(mes, hoje):
        mes = _somar_meses(mes, 1)
    return mes


def _mes_pedido(valor, hoje):
    try:
        ano, mes = (int(x) for x in (valor or '').split('-'))
        return date(ano, mes, 1)
    except (TypeError, ValueError):
        return proximo_mes_aberto(hoje)


@login_required
def minha_disponibilidade(request):
    hoje = timezone.localdate()
    mes = _mes_pedido(request.GET.get('mes'), hoje)
    fim = _somar_meses(mes, 1) - timedelta(days=1)
    minhas = {i.data: i for i in Indisponibilidade.objects.filter(usuario=request.user, data__range=(mes, fim))}
    cultos = set(Escala.objects.filter(data__range=(mes, fim)).values_list('data', flat=True))

    # Calendário: semanas de domingo a sábado
    semanas, semana = [], [None] * ((mes.weekday() + 1) % 7)
    dia = mes
    while dia <= fim:
        semana.append({'data': dia, 'culto': dia in cultos, 'indisponivel': minhas.get(dia)})
        if len(semana) == 7:
            semanas.append(semana)
            semana = []
        dia += timedelta(days=1)
    if semana:
        semanas.append(semana + [None] * (7 - len(semana)))

    return render(request, 'escalas/disponibilidade.html', {
        'mes': mes,
        'prazo': prazo_do_mes(mes),
        'aberto': mes_aberto(mes, hoje),
        'semanas': semanas,
        'minhas': sorted(minhas.values(), key=lambda i: i.data),
        'mes_anterior': _somar_meses(mes, -1),
        'mes_proximo': _somar_meses(mes, 1),
        'pode_avancar': _somar_meses(mes, 1) <= _somar_meses(_primeiro_dia(hoje), MESES_A_FRENTE),
        'hoje': hoje,
    })


def _voltar(dia):
    return redirect(f"{reverse('minha_disponibilidade')}?mes={dia:%Y-%m}")


@login_required
@require_POST
def disponibilidade_salvar(request):
    """Marca (ou altera a justificativa de) um dia indisponível."""
    try:
        dia = date.fromisoformat(request.POST.get('data', ''))
    except ValueError:
        messages.error(request, 'Data inválida.')
        return redirect('minha_disponibilidade')
    justificativa = ' '.join(request.POST.get('justificativa', '').split())[:200]
    if not mes_aberto(_primeiro_dia(dia)):
        messages.error(request, f'O prazo para informar {dia:%m/%Y} já terminou.')
    elif not justificativa:
        messages.error(request, 'Escreva a justificativa do dia.')
    else:
        Indisponibilidade.objects.update_or_create(usuario=request.user, data=dia,
                                                   defaults={'justificativa': justificativa})
        messages.success(request, f'{dia:%d/%m} marcado como indisponível.')
    return _voltar(dia)


@login_required
@require_POST
def disponibilidade_remover(request):
    try:
        dia = date.fromisoformat(request.POST.get('data', ''))
    except ValueError:
        return redirect('minha_disponibilidade')
    if not mes_aberto(_primeiro_dia(dia)):
        messages.error(request, f'O prazo para informar {dia:%m/%Y} já terminou.')
    else:
        Indisponibilidade.objects.filter(usuario=request.user, data=dia).delete()
        messages.success(request, f'{dia:%d/%m} voltou a ficar disponível.')
    return _voltar(dia)
