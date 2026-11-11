// Service worker do Louvor IPO (gerado por apps/core/pwa.py) — versão {{ versao }}
//
// Estratégias:
//   - páginas (HTML) e PDFs: rede primeiro; sem internet, usa a última versão salva
//   - arquivos estáticos (/static/, nomes com hash) e CDN: cache primeiro
//   - POST, admin e importação: nunca passam pelo cache
//   - ao sair da conta (logout) as páginas salvas são apagadas
const VERSAO = '{{ versao }}';
// Os arquivos guardados ficam num cache por versão: ao atualizar o app, os antigos são descartados
const CACHE_ESTATICOS = 'louvor-estaticos-' + VERSAO;
// Nome com hash (ex.: style.3f9a1c2b7d4e.css) nunca muda de conteúdo; sem hash pode mudar a cada deploy
const NOME_COM_HASH = /\.[0-9a-f]{12}\.[a-z0-9]+$/;
const CACHE_PAGINAS = 'louvor-paginas';
const PRECACHE = {{ precache_json|safe }};
const MAX_PAGINAS = 150;
const TEMPO_REDE_MS = 6000;
// Login e cadastro não funcionam sem internet: não há por que guardar
const NUNCA_GUARDAR = [/^\/$/, /^\/cadastro\//, /^\/admin/, /^\/logout/, /^\/musicas\/importar/,
                       /^\/integrantes\/accounts/, /^\/sw\.js/, /\/(previa|converter)\/$/];

self.addEventListener('install', evento => {
    evento.waitUntil((async () => {
        const cache = await caches.open(CACHE_ESTATICOS);
        // Um a um: se algum falhar, os outros continuam
        await Promise.all(PRECACHE.map(url =>
            fetch(url, { credentials: 'same-origin' })
                .then(r => (r.ok ? cache.put(url, r) : null))
                .catch(() => null)));
        await self.skipWaiting();
    })());
});

self.addEventListener('activate', evento => {
    evento.waitUntil((async () => {
        const nomes = await caches.keys();
        await Promise.all(nomes
            .filter(n => n.startsWith('louvor-') && ![CACHE_ESTATICOS, CACHE_PAGINAS].includes(n))
            .map(n => caches.delete(n)));
        await self.clients.claim();
    })());
});

function podeGuardar(url) {
    return url.origin === self.location.origin && !NUNCA_GUARDAR.some(r => r.test(url.pathname));
}

async function limitarPaginas() {
    const cache = await caches.open(CACHE_PAGINAS);
    const chaves = await cache.keys();
    for (const chave of chaves.slice(0, Math.max(0, chaves.length - MAX_PAGINAS))) {
        await cache.delete(chave);
    }
}

async function guardarPagina(requisicao, resposta) {
    const tipo = resposta.headers.get('content-type') || '';
    // Não guarda redirecionamentos (ex.: sessão expirada indo para o login) nem erros
    if (!resposta.ok || resposta.redirected || !(tipo.includes('text/html') || tipo.includes('application/pdf'))) return;
    const cache = await caches.open(CACHE_PAGINAS);
    await cache.delete(requisicao.url);  // reinsere no fim: as mais usadas ficam por último
    await cache.put(requisicao.url, resposta);
    await limitarPaginas();
}

function comTempoLimite(promessa, ms) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error('tempo esgotado')), ms);
        promessa.then(r => { clearTimeout(timer); resolve(r); }, e => { clearTimeout(timer); reject(e); });
    });
}

async function redePrimeiro(evento) {
    const requisicao = evento.request;
    const daRede = fetch(requisicao);
    try {
        const resposta = await comTempoLimite(daRede, TEMPO_REDE_MS);
        evento.waitUntil(guardarPagina(requisicao, resposta.clone()));
        return resposta;
    } catch (erro) {
        const salva = await caches.match(requisicao.url, { cacheName: CACHE_PAGINAS });
        if (salva) {
            // Internet lenta: mostra a versão salva, mas atualiza o cache se a rede responder depois
            evento.waitUntil(daRede.then(r => guardarPagina(requisicao, r)).catch(() => null));
            return salva;
        }
        if (requisicao.mode === 'navigate') {
            try { return await daRede; } catch (e) { /* sem rede de verdade */ }
            return (await caches.match('/offline/')) || new Response('Sem internet', { status: 503 });
        }
        return daRede;
    }
}

// Arquivo do site sem hash no nome: busca a versão nova; sem internet, usa a guardada
async function estaticoRedePrimeiro(requisicao) {
    try {
        // cache: 'no-cache' = confere com o servidor (resposta curta "não mudou" se for igual),
        // em vez de aceitar a cópia do cache HTTP do navegador, que pode ser da versão anterior
        const resposta = await comTempoLimite(fetch(requisicao, { cache: 'no-cache' }), 3500);
        if (resposta.ok) {
            const cache = await caches.open(CACHE_ESTATICOS);
            await cache.put(requisicao, resposta.clone());
        }
        return resposta;
    } catch (erro) {
        const salva = await caches.match(requisicao);
        if (salva) return salva;
        throw erro;
    }
}

async function cachePrimeiro(requisicao) {
    const salva = await caches.match(requisicao);
    if (salva) return salva;
    const resposta = await fetch(requisicao);
    if (resposta.ok || resposta.type === 'opaque') {
        const cache = await caches.open(CACHE_ESTATICOS);
        await cache.put(requisicao, resposta.clone());
    }
    return resposta;
}

self.addEventListener('fetch', evento => {
    const requisicao = evento.request;
    const url = new URL(requisicao.url);

    // Saiu da conta: apaga as páginas guardadas deste usuário. Apaga antes e de novo depois da
    // resposta, porque uma página aberta logo antes pode terminar de ser salva durante o logout.
    if (requisicao.method === 'POST' && url.origin === self.location.origin && url.pathname === '/logout/') {
        evento.respondWith((async () => {
            await caches.delete(CACHE_PAGINAS);
            const resposta = await fetch(requisicao);
            await caches.delete(CACHE_PAGINAS);
            setTimeout(() => caches.delete(CACHE_PAGINAS), 3000);
            return resposta;
        })());
        return;
    }
    if (requisicao.method !== 'GET') return;

    if (url.origin === self.location.origin && url.pathname.startsWith('/static/')) {
        evento.respondWith(NOME_COM_HASH.test(url.pathname) ? cachePrimeiro(requisicao) : estaticoRedePrimeiro(requisicao));
        return;
    }
    if (url.hostname === 'cdn.jsdelivr.net' || url.hostname === 'cdnjs.cloudflare.com') {
        evento.respondWith(cachePrimeiro(requisicao));  // URLs com versão fixa (bootstrap@5.3.3...)
        return;
    }
    if (url.origin === self.location.origin && url.pathname.startsWith('/media/')) {
        evento.respondWith(cachePrimeiro(requisicao));
        return;
    }
    if (podeGuardar(url) && (requisicao.mode === 'navigate' || url.pathname.endsWith('/pdf/') || (requisicao.headers.get('accept') || '').includes('text/html'))) {
        evento.respondWith(redePrimeiro(evento));
    }
});

// A página pede para guardar com antecedência (ex.: cifras dos próximos cultos)
self.addEventListener('message', evento => {
    const dados = evento.data || {};
    if (dados.tipo === 'guardar' && Array.isArray(dados.urls)) {
        evento.waitUntil(Promise.all(dados.urls.slice(0, 20).map(async caminho => {
            const url = new URL(caminho, self.location.origin);
            if (!podeGuardar(url)) return;
            try {
                const resposta = await fetch(url.href, { credentials: 'same-origin' });
                await guardarPagina(new Request(url.href), resposta);
            } catch (e) { /* sem internet agora: tenta na próxima vez */ }
        })));
    }
});
