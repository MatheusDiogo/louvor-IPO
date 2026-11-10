from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from apps.core.decorators import requer_lider
from apps.core.utils import chave_alfabetica
from .cifra import (
    converter_cifra_comum, extrair_metadados, normalizar_tom, opcoes_de_tom,
    parece_chordpro, renderizar_html, tom_base,
)
from .cifra_pdf import gerar_pdf
from .models import Musica


def _tom_pedido(request, musica):
    """Tom pedido na URL (?tom=G) se for válido; senão o tom original da música."""
    pedido = request.GET.get('tom', '').strip()
    return normalizar_tom(pedido) if tom_base(pedido) else musica.tom


@login_required
def musicas_view(request):
    musicas = sorted(Musica.objects.all(), key=lambda m: chave_alfabetica(m.nome))
    a_revisar = sum(1 for m in musicas if m.revisar)
    return render(request, "musicas.html", {"musicas": musicas, "a_revisar": a_revisar})


@login_required
def detalhes_musica(request, musica_id):
    """Leitor da cifra, com troca de tom."""
    musica = get_object_or_404(Musica, id=musica_id)
    tom = _tom_pedido(request, musica)
    opcoes = opcoes_de_tom(musica.tom)
    if tom and tom not in opcoes:
        opcoes = [tom] + opcoes
    return render(request, 'musica_detalhe.html', {
        'musica': musica,
        'tom': tom,
        'opcoes_tom': opcoes,
        'cifra_html': renderizar_html(musica.cifra, musica.tom, tom),
    })


@login_required
def musica_pdf(request, musica_id):
    musica = get_object_or_404(Musica, id=musica_id)
    tom = _tom_pedido(request, musica)
    pdf = gerar_pdf([{'nome': musica.nome, 'cifra': musica.cifra, 'tom_original': musica.tom, 'tom': tom}])
    resposta = HttpResponse(pdf, content_type='application/pdf')
    nome = slugify(f'{musica.nome}-{tom}') or 'cifra'
    resposta['Content-Disposition'] = f'inline; filename="{nome}.pdf"'
    return resposta


@login_required
@requer_lider
def musica_editar(request, musica_id=None):
    """Cria ou edita uma música (nome, tom, YouTube e cifra em ChordPro)."""
    musica = get_object_or_404(Musica, id=musica_id) if musica_id else Musica()

    if request.method == 'POST':
        cifra, titulo_cifra, tom_cifra = extrair_metadados(request.POST.get('cifra', ''))
        nome = request.POST.get('nome', '').strip() or titulo_cifra
        tom = request.POST.get('tom', '').strip() or tom_cifra
        youtube = request.POST.get('link_youtube', '').strip() or None

        erros = []
        if not nome:
            erros.append('Informe o nome da música.')
        duplicada = Musica.objects.exclude(pk=musica.pk).filter(nome__iexact=nome).first() if nome else None
        if duplicada:
            erros.append(f'Já existe uma música chamada "{duplicada.nome}".')

        musica.nome, musica.tom, musica.cifra, musica.link_youtube = nome, tom[:10], cifra, youtube
        if erros:
            for erro in erros:
                messages.error(request, erro)
        else:
            musica.revisar = False
            musica.save()
            messages.success(request, f'"{musica.nome}" salva.')
            return redirect('detalhes_musica', musica_id=musica.id)

    return render(request, 'musica_editar.html', {
        'musica': musica,
        'opcoes_tom': opcoes_de_tom(''),
    })


@login_required
@requer_lider
@require_POST
def musica_previa(request):
    """HTML da cifra enquanto o líder digita no editor."""
    return JsonResponse({'html': renderizar_html(request.POST.get('cifra', ''), request.POST.get('tom', ''))})


@login_required
@requer_lider
@require_POST
def musica_converter(request):
    """Converte "acordes em cima da letra" (colado do Cifra Club, Word...) para ChordPro."""
    texto = request.POST.get('texto', '')
    cifra, titulo, tom = converter_cifra_comum(texto)
    return JsonResponse({'cifra': cifra, 'titulo': titulo, 'tom': tom, 'ja_era_chordpro': parece_chordpro(texto)})


@login_required
@requer_lider
@require_POST
def excluir_musica(request, id):
    musica = get_object_or_404(Musica, id=id)
    musica.delete()
    messages.success(request, f'"{musica.nome}" excluída.')
    return redirect('musicas')
