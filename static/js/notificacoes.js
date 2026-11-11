// Notificações deste aparelho: convite na tela inicial, sino na barra do topo e vínculo com o usuário logado.
(function () {
    const chavePublica = document.body.dataset.vapid;
    if (!chavePublica) return;  // notificações ainda não configuradas no servidor

    const suportado = 'serviceWorker' in navigator && 'PushManager' in window && 'Notification' in window;
    const ehIOS = /iphone|ipad|ipod/i.test(navigator.userAgent);
    const instalado = window.matchMedia('(display-mode: standalone)').matches || navigator.standalone === true;
    const CHAVE_ENDPOINT = 'push-endpoint';
    const CHAVE_DISPENSADO = 'notif-convite-dispensado';

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

    // ------------------------------------------------------------ interface (sino, janela e convite)
    const sino = document.getElementById('botaoNotificacoes');
    const painel = document.getElementById('modalNotificacoes');
    const cartao = document.getElementById('cartaoNotificacoes');
    let estadoAtual = 'inativo';

    const TEXTOS = {
        ativo: ['Ativadas neste aparelho', 'bg-success', 'Você recebe os avisos do louvor neste aparelho.'],
        inativo: ['Desativadas', 'bg-secondary', 'Ative para receber os avisos do louvor neste aparelho:'],
        bloqueado: ['Bloqueadas no aparelho', 'bg-danger',
            'As notificações do Louvor IPO estão bloqueadas nas configurações do celular (ou do navegador). ' +
            'Libere por lá e depois toque no sino de novo.'],
        'ios-instalar': ['Instale o app', 'bg-warning text-dark',
            'No iPhone as notificações só funcionam com o app instalado: toque em Compartilhar → ' +
            '"Adicionar à Tela de Início" e ative pelo app.'],
        'sem-suporte': ['Indisponíveis', 'bg-secondary',
            'Este navegador não recebe notificações. Use o Chrome (Android) ou o app instalado no iPhone.'],
    };

    function mostrar(estado) {
        estadoAtual = estado;
        const [selo, corSelo, texto] = TEXTOS[estado];

        if (sino) {
            const icone = sino.querySelector('i');
            icone.className = estado === 'ativo' ? 'bi bi-bell-fill text-success'
                : estado === 'bloqueado' ? 'bi bi-bell-slash' : 'bi bi-bell';
            sino.title = estado === 'ativo' ? 'Notificações ativadas' : 'Notificações desativadas';
            sino.hidden = false;
        }
        if (painel) {
            const elSelo = painel.querySelector('[data-painel-selo]');
            elSelo.className = `badge rounded-pill ${corSelo}`;
            elSelo.textContent = selo;
            painel.querySelector('[data-painel-texto]').textContent = texto;
            painel.querySelector('[data-painel-lista]').hidden = !['ativo', 'inativo'].includes(estado);
            painel.querySelector('[data-notif="ativar"]').hidden = estado !== 'inativo';
            painel.querySelector('[data-notif="desativar"]').hidden = estado !== 'ativo';
            painel.querySelector('[data-notif="testar"]').hidden = estado !== 'ativo';
        }
        // Convite na tela inicial: só para quem ainda pode ativar e não dispensou
        if (cartao && !cartao.dataset.mensagem) {
            const convidar = (estado === 'inativo' || estado === 'ios-instalar') && ler(CHAVE_DISPENSADO) !== '1';
            cartao.hidden = !convidar;
            if (convidar && estado === 'ios-instalar') {
                cartao.querySelector('[data-cartao-texto]').textContent = TEXTOS['ios-instalar'][2];
                cartao.querySelector('[data-notif="ativar"]').hidden = true;
            }
        }
    }

    // Mensagem rápida no lugar do convite antes de ele sumir
    function avisoNoCartao(titulo, texto) {
        if (!cartao || cartao.hidden) return;
        cartao.dataset.mensagem = '1';
        cartao.querySelector('[data-cartao-titulo]').textContent = titulo;
        cartao.querySelector('[data-cartao-texto]').textContent = texto;
        cartao.querySelector('[data-cartao-botoes]').hidden = true;
        setTimeout(() => { cartao.hidden = true; }, 4000);
    }

    async function ativar(botao) {
        botao.disabled = true;
        try {
            const permissao = await Notification.requestPermission();
            if (permissao !== 'granted') {
                mostrar(permissao === 'denied' ? 'bloqueado' : 'inativo');
                return;
            }
            const registro = await navigator.serviceWorker.ready;
            let inscricao = await registro.pushManager.getSubscription();
            if (inscricao && !mesmaChave(inscricao)) { await inscricao.unsubscribe(); inscricao = null; }
            if (!inscricao) {
                inscricao = await registro.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: chaveEmBytes(chavePublica) });
            }
            if (!(await registrarNoServidor(inscricao))) throw new Error('servidor');
            gravar(CHAVE_DISPENSADO, null);
            avisoNoCartao('Notificações ativadas ✅', 'Enviamos uma notificação de teste para este aparelho.');
            mostrar('ativo');
            postar('/notificacoes/testar/');  // teste automático confirma que chegou
        } catch (erro) {
            alert('Não foi possível ativar as notificações agora. Verifique a internet e tente de novo.');
            mostrar('inativo');
        } finally {
            botao.disabled = false;
        }
    }

    async function desativar() {
        const inscricao = await inscricaoAtual().catch(() => null);
        if (inscricao) {
            await postar('/notificacoes/cancelar/', { endpoint: inscricao.endpoint }).catch(() => null);
            await inscricao.unsubscribe().catch(() => null);
        }
        gravar(CHAVE_ENDPOINT, null);
        gravar(CHAVE_DISPENSADO, '1');  // quem desativou não precisa ver o convite de novo
        mostrar('inativo');
    }

    document.addEventListener('click', e => {
        const acao = e.target.closest('[data-notif]');
        if (!acao) return;
        const tipo = acao.dataset.notif;
        if (tipo === 'ativar') ativar(acao);
        if (tipo === 'desativar') desativar();
        if (tipo === 'dispensar') {
            gravar(CHAVE_DISPENSADO, '1');
            avisoNoCartao('Tudo bem!', 'Se mudar de ideia, toque no sino 🔔 no topo da tela.');
        }
        if (tipo === 'testar') {
            acao.disabled = true;
            postar('/notificacoes/testar/').then(r => r.json()).then(d => {
                if (!d.ok) alert('Não chegou nenhuma notificação. Desative e ative de novo.');
            }).finally(() => { acao.disabled = false; });
        }
    });

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
