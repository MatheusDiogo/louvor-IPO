"""App instalável (PWA): manifesto, service worker e página "sem internet"."""
import hashlib
import json

from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.templatetags.static import static
from django.views.decorators.cache import cache_control

# Arquivos guardados no celular na instalação (o resto é guardado conforme o uso)
CDN = [
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css',
    'https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js',
    'https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css',
]
ESTATICOS = ['css/style.css', 'js/script.js', 'js/cifra.js', 'img/icone-192.png', 'img/favicon-32.png']

# Aumente quando mudar a lógica do service worker sem mudar os arquivos estáticos
VERSAO_SW = 1


@cache_control(max_age=3600)
def manifesto(request):
    dados = {
        'name': 'Louvor IPO',
        'short_name': 'Louvor IPO',
        'description': 'Escalas, cultos e cifras do ministério de louvor.',
        'lang': 'pt-BR',
        'start_url': '/home/',
        'scope': '/',
        'display': 'standalone',
        'orientation': 'portrait',
        'background_color': '#f0fdf4',
        'theme_color': '#166534',
        'icons': [
            {'src': static('img/icone-192.png'), 'sizes': '192x192', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('img/icone-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'any'},
            {'src': static('img/icone-maskable-512.png'), 'sizes': '512x512', 'type': 'image/png', 'purpose': 'maskable'},
        ],
        'shortcuts': [
            {'name': 'Culto', 'url': '/escalas/', 'icons': [{'src': static('img/icone-192.png'), 'sizes': '192x192'}]},
            {'name': 'Músicas', 'url': '/musicas/', 'icons': [{'src': static('img/icone-192.png'), 'sizes': '192x192'}]},
        ],
    }
    return HttpResponse(json.dumps(dados, ensure_ascii=False), content_type='application/manifest+json')


@cache_control(no_cache=True, max_age=0)
def service_worker(request):
    estaticos = [static(caminho) for caminho in ESTATICOS]
    # A versão muda quando algum arquivo estático muda (nomes com hash) -> o celular atualiza o app
    versao = hashlib.sha1(json.dumps([VERSAO_SW, estaticos]).encode()).hexdigest()[:10]
    conteudo = render_to_string('pwa/sw.js', {
        'versao': versao,
        'precache_json': json.dumps(['/offline/'] + estaticos + CDN),
    })
    resposta = HttpResponse(conteudo, content_type='application/javascript; charset=utf-8')
    resposta['Service-Worker-Allowed'] = '/'
    return resposta


def offline(request):
    return render(request, 'pwa/offline.html')
