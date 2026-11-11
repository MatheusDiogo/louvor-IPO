// Ativar/desativar as notificações deste aparelho e mantê-lo ligado ao usuário logado.
(function () {
    const chavePublica = document.body.dataset.vapid;
    if (!chavePublica) return;  // notificações ainda não configuradas no servidor

    const suportado = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    const ehIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const instalado = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    const CHAVE_ENDPOINT = 'push-endpoint';

    const ler = (k) => { try { return localStorage.getItem(k); } catch (e) { return null; } };
    const gravar = (k, v) => { try { v === null ? localStorage.removeItem(k) : localStorage.setItem(k, v); } catch (e) { /* ok */ } };
    const csrf = () => (document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/) || [])[1] || '';

    function chaveEmBytes(base64) {
        const preenchida = (base64 + '='.repeat((4 - base64.length % 4) % 4)).replace(/-/g, '+').replace(/_/g, '/');
        return Uint8Array.from(atob(preenchida), c => c.charCodeAt(0));
    }

    const postar = (url, corpo) => fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify(corpo || {}),
    });

    async function inscricaoAtual() {
        const registro = await navigator.serviceWorker.ready;
        return registro.pushManager.getSubscription();
    }

    function mesmaChave(inscricao) {
        const atual = inscricao.options && inscricao.options.applicationServerKey;
        if (!atual) return true;
        const a = new Uint8Array(atual), b = chaveEmBytes(chavePublica);
        return a.length === b.length && a.every((v, i) => v === b[i]);
    }

    async function registrarNoServidor(inscricao) {
        const resposta = await postar('/notificacoes/inscrever/', inscricao.toJSON());
        if (resposta.ok) gravar(CHAVE_ENDPOINT, inscricao.endpoint);
        return resposta.ok;
    }

    // ------------------------------------------------------------ cartão na tela inicial
    const cartao = document.getElementById('cartaoNotificacoes');

    function mostrar(estado) {
        if (!cartao) return;
        const titulo = cartao.querySelector('[data-notif-titulo]');
        const texto = cartao.querySelector('[data-notif-texto]');
        const botoes = { ativar: 'ativar', testar: 'testar', desativar: 'desativar' };
        const ver = (nomes) => Object.keys(botoes).forEach(b => {
            cartao.querySelector(`[data-notif="${b}"]`).hidden = !nomes.includes(b);
        });
        cartao.classList.toggle('notif-ativa', estado === 'ativo');
        cartao.hidden = false;
        if (estado === 'ativo') {
            titulo.textContent = 'Notificações ativadas neste aparelho';
            texto.textContent = 'Você vai receber os avisos das músicas do culto e da escala do mês.';
            ver(['testar', 'desativar']);
        } else if (estado === 'bloqueado') {
            titulo.textContent = 'Notificações bloqueadas';
            texto.textContent = 'Para receber os avisos, libere as notificações do Louvor IPO nas configurações do celular (ou do navegador) e recarregue a página.';
            ver([]);
        } else if (estado === 'ios-instalar') {
            titulo.textContent = 'Receba os avisos no iPhone';
            texto.textContent = 'No iPhone as notificações só funcionam com o app instalado: toque em Compartilhar → "Adicionar à Tela de Início" e abra o Louvor IPO por lá.';
            ver([]);
        } else if (estado === 'sem-suporte') {
            titulo.textContent = 'Notificações indisponíveis';
            texto.textContent = 'Este navegador não recebe notificações. Use o Chrome (Android) ou o app instalado no iPhone.';
            ver([]);
        } else {
            titulo.textContent = 'Receba os avisos do louvor';
            texto.textContent = 'Músicas e tons do culto em que você está escalado e a escala do mês.';
            ver(['ativar']);
        }
    }

    async function ativar(botao) {
        botao.disabled = true;
        try {
            const permissao = await Notification.requestPermission();
            if (permissao !== 'granted') { mostrar(permissao === 'denied' ? 'bloqueado' : 'inativo'); return; }
            const registro = await navigator.serviceWorker.ready;
            let inscricao = await registro.pushManager.getSubscription();
            if (inscricao && !mesmaChave(inscricao)) { await inscricao.unsubscribe(); inscricao = null; }
            if (!inscricao) {
                inscricao = await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: chaveEmBytes(chavePublica) });
            }
            if (!(await registrarNoServidor(inscricao))) throw new Error('servidor');
            mostrar('ativo');
            postar('/notificacoes/testar/');  // confirma com uma notificação de teste
        } catch (erro) {
            alert('Não foi possível ativar as notificações agora. Verifique a internet e tente de novo.');
            mostrar('inativo');
        } finally {
            botao.disabled = false;
        }
    }

    async function desativar() {
        const inscricao = await inscricaoAtual();
        if (inscricao) {
            await postar('/notificacoes/cancelar/', { endpoint: inscricao.endpoint }).catch(() => null);
            await inscricao.unsubscribe().catch(() => null);
        }
        gravar(CHAVE_ENDPOINT, null);
        mostrar('inativo');
    }

    if (cartao) {
        cartao.addEventListener('click', e => {
            const acao = e.target.closest('[data-notif]');
            if (!acao) return;
            if (acao.dataset.notif === 'ativar') ativar(acao);
            if (acao.dataset.notif === 'desativar') desativar();
            if (acao.dataset.notif === 'testar') {
                postar('/notificacoes/testar/').then(r => r.json()).then(d => {
                    if (!d.ok) alert('Não chegou nenhuma notificação. Desative e ative de novo.');
                });
            }
        });
    }

    // ------------------------------------------------------------ estado inicial e sincronização
    (async () => {
        if (!suportado) { mostrar(ehIOS && !instalado ? 'ios-instalar' : 'sem-suporte'); return; }
        if (Notification.permission === 'denied') { mostrar('bloqueado'); return; }
        const inscricao = Notification.permission === 'granted' ? await inscricaoAtual().catch(() => null) : null;
        if (!inscricao) { mostrar('inativo'); return; }
        mostrar('ativo');
        // Uma vez por sessão: confirma que este aparelho está ligado a quem está logado agora
        try {
            if (!mesmaChave(inscricao)) { await inscricao.unsubscribe(); mostrar('inativo'); return; }
            if (sessionStorage.getItem('push-sincronizado') !== '1') {
                if (await registrarNoServidor(inscricao)) sessionStorage.setItem('push-sincronizado', '1');
            }
        } catch (e) { /* tenta na próxima página */ }
    })();

    // Ao sair da conta, este aparelho deixa de receber os avisos desta pessoa
    document.querySelectorAll('form[action="/logout/"]').forEach(form => form.addEventListener('submit', () => {
        const endpoint = ler(CHAVE_ENDPOINT);
        if (!endpoint) return;
        const campo = document.createElement('input');
        campo.type = 'hidden'; campo.name = 'push_endpoint'; campo.value = endpoint;
        form.append(campo);
        try { sessionStorage.removeItem('push-sincronizado'); } catch (e) { /* ok */ }
    }));
})();
