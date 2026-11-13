// Leitor de cifras: tamanho da letra, mostrar/ocultar acordes, manter a tela acesa e troca de tom.
(function () {
    const ler = (chave, padrao) => {
        try { const v = localStorage.getItem(chave); return v === null ? padrao : v; } catch (e) { return padrao; }
    };
    const gravar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch (e) { /* sem armazenamento */ } };

    // Tamanho da letra. As linhas com acorde nunca quebram (senão o acorde sai do lugar), então o
    // tamanho máximo é o maior em que a linha mais comprida da música ainda cabe na tela.
    // 'max' = sempre usar esse limite (padrão); um número = tamanho escolhido pela pessoa com A−.
    const ESCALA_MIN = 0.55, ESCALA_MAX = 1.8, PASSO = 0.1;
    let preferencia = ler('cifra-tamanho', 'max');
    let acordes = ler('cifra-acordes', '1') === '1';

    function limiteSemQuebra(leitor) {
        leitor.style.setProperty('--cifra-escala', 1);
        // .medindo deixa cada linha com a largura do próprio conteúdo (e não a da tela)
        leitor.classList.add('medindo');
        let maisLarga = 0;
        leitor.querySelectorAll('.cp-line:not(.cp-lyrics-only)').forEach(linha => {
            maisLarga = Math.max(maisLarga, linha.getBoundingClientRect().width);
        });
        leitor.classList.remove('medindo');
        if (!maisLarga) return ESCALA_MAX;
        // a largura da linha cresce na mesma proporção da fonte; folga de 2% para arredondamentos
        return Math.min(ESCALA_MAX, Math.floor((leitor.clientWidth / maisLarga) * 98) / 100);
    }

    function leitorDeReferencia() {
        const visiveis = Array.from(document.querySelectorAll('.cifra-leitor')).filter(el => el.clientWidth > 0);
        return (focada && focada.querySelector('.cifra-leitor')) || visiveis[0] || null;
    }

    function aplicar() {
        document.querySelectorAll('.cifra-leitor').forEach(el => {
            el.classList.toggle('sem-acordes', !acordes);
            if (!el.clientWidth) return;  // escondido (ex.: aba de pré-visualização fechada)
            const limite = limiteSemQuebra(el);
            const desejada = preferencia === 'max' ? limite : parseFloat(preferencia);
            el.dataset.limite = limite;
            el.style.setProperty('--cifra-escala', Math.max(ESCALA_MIN, Math.min(desejada, limite)));
        });
        const ref = leitorDeReferencia();
        const noLimite = preferencia === 'max' || (ref && parseFloat(preferencia) >= parseFloat(ref.dataset.limite));
        document.querySelectorAll('[data-cifra="maior"]').forEach(b => {
            b.disabled = !!noLimite;
            b.title = noLimite ? 'Tamanho máximo sem quebrar as linhas' : 'Aumentar letra';
        });
        document.querySelectorAll('[data-cifra="acordes"]').forEach(b => b.classList.toggle('ativo', acordes));
    }

    function mudarTamanho(passo) {
        const ref = leitorDeReferencia();
        if (!ref) return;
        const atual = parseFloat(getComputedStyle(ref).getPropertyValue('--cifra-escala')) || 1;
        const limite = parseFloat(ref.dataset.limite) || ESCALA_MAX;
        const nova = +(atual + passo).toFixed(2);
        preferencia = nova >= limite - 0.001 ? 'max' : String(Math.max(ESCALA_MIN, nova));
        gravar('cifra-tamanho', preferencia);
    }

    // Recalcula ao girar o celular / redimensionar e quando as fontes terminam de carregar
    let esperaRedimensionar;
    window.addEventListener('resize', () => {
        clearTimeout(esperaRedimensionar);
        esperaRedimensionar = setTimeout(aplicar, 150);
    });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(aplicar);
    window.ajustarCifras = aplicar;  // usado pela pré-visualização do editor

    // Manter a tela acesa (Wake Lock API)
    let trava = null;
    const telaAcesa = () => trava !== null;
    async function alternarTela(botao) {
        try {
            if (telaAcesa()) {
                await trava.release();
                trava = null;
            } else {
                trava = await navigator.wakeLock.request('screen');
                trava.addEventListener('release', () => { trava = null; atualizarBotaoTela(); });
            }
        } catch (e) {
            alert('Este navegador não permite manter a tela acesa.');
        }
        atualizarBotaoTela();
    }
    function atualizarBotaoTela() {
        document.querySelectorAll('[data-cifra="tela"]').forEach(b => b.classList.toggle('ativo', telaAcesa()));
    }
    document.addEventListener('visibilitychange', async () => {
        // o navegador solta a trava ao trocar de aba; religa ao voltar se estava ativa
        if (document.visibilityState === 'visible' && ler('cifra-tela', '0') === '1' && !telaAcesa()) {
            try { trava = await navigator.wakeLock.request('screen'); } catch (e) { /* ignorado */ }
            atualizarBotaoTela();
        }
    });

    // ---------------------------------------------------------------- Cores da caixa da cifra
    // Fundo, letra e acordes escolhidos pela pessoa (guardados no aparelho, valem em todas as cifras).
    const TEMAS = {
        padrao: { nome: 'Padrão', fundo: '#ffffff', letra: '#212529', acorde: '#166534' },
        escuro: { nome: 'Escuro', fundo: '#121212', letra: '#f1f3f5', acorde: '#4ade80' },
        sepia: { nome: 'Sépia', fundo: '#f4ecd8', letra: '#3b2f1e', acorde: '#9a3412' },
        contraste: { nome: 'Alto contraste', fundo: '#000000', letra: '#ffffff', acorde: '#facc15' },
        noite: { nome: 'Noite', fundo: '#0f172a', letra: '#e2e8f0', acorde: '#38bdf8' },
    };
    const COR_RE = /^#[0-9a-f]{6}$/i;
    let cores = null;  // null = padrão do site
    try {
        const salvas = JSON.parse(ler('cifra-cores', 'null'));
        if (salvas && ['fundo', 'letra', 'acorde'].every(k => COR_RE.test(salvas[k]))) cores = salvas;
    } catch (e) { /* valor inválido: usa o padrão */ }

    function aplicarCores() {
        const raiz = document.documentElement;
        const iguais = c => c && ['fundo', 'letra', 'acorde'].every(k => c[k].toLowerCase() === TEMAS.padrao[k]);
        if (!cores || iguais(cores)) {
            raiz.removeAttribute('data-cifra-cores');
            ['--cifra-fundo', '--cifra-letra', '--cifra-acorde'].forEach(v => raiz.style.removeProperty(v));
            return;
        }
        raiz.setAttribute('data-cifra-cores', '');
        raiz.style.setProperty('--cifra-fundo', cores.fundo);
        raiz.style.setProperty('--cifra-letra', cores.letra);
        raiz.style.setProperty('--cifra-acorde', cores.acorde);
    }
    aplicarCores();

    let modalCores = null;
    function abrirCores() {
        if (!modalCores) {
            const caixa = document.createElement('div');
            caixa.className = 'modal fade';
            caixa.id = 'modalCores';
            caixa.tabIndex = -1;
            caixa.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content border-0 shadow">
                        <div class="modal-header border-0 pt-4 px-4">
                            <h5 class="fw-bold mb-0" style="color: var(--primary-green);"><i class="bi bi-palette me-2"></i>Cores da cifra</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Fechar"></button>
                        </div>
                        <div class="modal-body px-4">
                            <div class="small fw-bold text-secondary mb-2">Temas</div>
                            <div class="d-flex flex-wrap gap-2 mb-3" id="coresTemas"></div>
                            <div class="small fw-bold text-secondary mb-2">Personalizar</div>
                            <div class="row g-2 mb-3">
                                <label class="col-4 cor-campo"><input type="color" data-cor="fundo"><span>Fundo</span></label>
                                <label class="col-4 cor-campo"><input type="color" data-cor="letra"><span>Letra</span></label>
                                <label class="col-4 cor-campo"><input type="color" data-cor="acorde"><span>Acordes</span></label>
                            </div>
                            <div class="cores-previa" id="coresPrevia">
                                <div class="cores-previa-acordes">G&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;D/F#&nbsp;&nbsp;&nbsp;&nbsp;Em</div>
                                <div>Grande é o Senhor e digno de louvor</div>
                            </div>
                            <p class="small text-muted mt-2 mb-0">Fica guardado neste aparelho e vale para todas as cifras.</p>
                        </div>
                        <div class="modal-footer border-0 pb-4 px-4">
                            <button type="button" class="btn btn-light px-3 rounded-pill" id="coresPadrao">Restaurar padrão</button>
                            <button type="button" class="btn-login btn-acao" data-bs-dismiss="modal">Pronto</button>
                        </div>
                    </div>
                </div>`;
            document.body.appendChild(caixa);
            const temas = caixa.querySelector('#coresTemas');
            Object.entries(TEMAS).forEach(([chave, t]) => {
                const b = document.createElement('button');
                b.type = 'button';
                b.className = 'tema-cor';
                b.dataset.tema = chave;
                b.innerHTML = `<span class="tema-amostra" style="background:${t.fundo};color:${t.letra};"><b style="color:${t.acorde};">G</b> Aa</span><span class="tema-nome">${t.nome}</span>`;
                b.addEventListener('click', () => escolherCores(chave === 'padrao' ? null : { fundo: t.fundo, letra: t.letra, acorde: t.acorde }));
                temas.appendChild(b);
            });
            caixa.querySelectorAll('[data-cor]').forEach(campo => campo.addEventListener('input', () => {
                const atual = { ...(cores || TEMAS.padrao) };
                atual[campo.dataset.cor] = campo.value;
                escolherCores({ fundo: atual.fundo, letra: atual.letra, acorde: atual.acorde });
            }));
            caixa.querySelector('#coresPadrao').addEventListener('click', () => escolherCores(null));
            modalCores = { caixa, modal: new bootstrap.Modal(caixa) };
        }
        atualizarModalCores();
        modalCores.modal.show();
    }

    function escolherCores(novas) {
        cores = novas;
        gravar('cifra-cores', cores ? JSON.stringify(cores) : 'null');
        aplicarCores();
        atualizarModalCores();
    }

    function atualizarModalCores() {
        if (!modalCores) return;
        const atual = cores || TEMAS.padrao;
        modalCores.caixa.querySelectorAll('[data-cor]').forEach(campo => { campo.value = atual[campo.dataset.cor]; });
        const previa = modalCores.caixa.querySelector('#coresPrevia');
        previa.style.background = atual.fundo;
        previa.style.color = atual.letra;
        previa.querySelector('.cores-previa-acordes').style.color = atual.acorde;
        modalCores.caixa.querySelectorAll('.tema-cor').forEach(b => {
            const t = TEMAS[b.dataset.tema];
            b.classList.toggle('ativo', ['fundo', 'letra', 'acorde'].every(k => t[k].toLowerCase() === atual[k].toLowerCase()));
        });
    }

    document.addEventListener('click', e => {
        const botao = e.target.closest('[data-cifra]');
        if (!botao) return;
        const acao = botao.dataset.cifra;
        if (acao === 'cores') {
            abrirCores();
            return;
        }
        if (acao === 'foco') {
            const alvo = botao.dataset.focoAlvo ? document.querySelector(botao.dataset.focoAlvo) : botao.closest('[data-foco]');
            if (alvo) abrirFoco(alvo, true);
            return;
        }
        if (acao === 'menor') mudarTamanho(-PASSO);
        if (acao === 'maior') mudarTamanho(PASSO);
        if (acao === 'acordes') acordes = !acordes;
        if (acao === 'tela') {
            alternarTela(botao).then(() => gravar('cifra-tela', telaAcesa() ? '1' : '0'));
            return;
        }
        gravar('cifra-acordes', acordes ? '1' : '0');
        aplicar();
    });

    document.addEventListener('change', e => {
        const seletor = e.target.closest('[data-trocar-tom]');
        if (!seletor) return;
        const url = new URL(window.location.href);
        url.searchParams.set('tom', seletor.value);
        window.location.href = url.toString();
    });

    // ---------------------------------------------------------------- Tela cheia (uma cifra por vez)
    // A cifra escolhida cobre a tela inteira. Onde o navegador permite (Android, computador),
    // também entra em tela cheia de verdade; no iPhone fica só a cobertura da página.
    let focada = null;

    const controles = document.createElement('div');
    controles.className = 'foco-controles';
    controles.hidden = true;
    controles.innerHTML = `
        <div class="foco-linha foco-rolagem">
            <button type="button" class="btn btn-light border" data-rolar="menos" aria-label="Rolar mais devagar"><i class="bi bi-dash-lg"></i></button>
            <button type="button" class="btn btn-success foco-play" data-rolar="play" aria-label="Rolar a cifra"><i class="bi bi-play-fill"></i></button>
            <span class="foco-velocidade small fw-semibold" aria-live="polite"></span>
            <button type="button" class="btn btn-light border" data-rolar="mais" aria-label="Rolar mais rápido"><i class="bi bi-plus-lg"></i></button>
        </div>
        <div class="foco-linha">
            <button type="button" class="btn btn-light border" data-foco-acao="anterior" aria-label="Música anterior"><i class="bi bi-chevron-left"></i></button>
            <span class="foco-posicao small fw-semibold text-truncate"></span>
            <button type="button" class="btn btn-light border" data-foco-acao="proxima" aria-label="Próxima música"><i class="bi bi-chevron-right"></i></button>
            <span class="foco-separador"></span>
            <button type="button" class="btn btn-light border" data-cifra="menor" aria-label="Diminuir letra">A−</button>
            <button type="button" class="btn btn-light border" data-cifra="maior" aria-label="Aumentar letra">A+</button>
            <button type="button" class="btn btn-light border" data-cifra="acordes" aria-label="Mostrar/ocultar acordes"><i class="bi bi-music-note-beamed"></i></button>
            <button type="button" class="btn btn-success" data-foco-acao="fechar" aria-label="Sair da tela cheia"><i class="bi bi-x-lg"></i></button>
        </div>`;
    document.body.appendChild(controles);

    // ---------------------------------------------------------------- Rolagem automática ("play")
    // Velocidade de 1 a 10, guardada por música neste aparelho (cada músico escolhe a sua).
    // Só aparece quando a cifra não cabe na tela. O play continua ligado mesmo no fim da música
    // (se o músico voltar para o começo, ela segue rolando); só desliga ao tocar de novo,
    // trocar de música ou sair da tela cheia. Enquanto rola, a tela fica acesa.
    // O menu some sozinho depois de alguns segundos; tocar na cifra mostra/esconde.
    const VEL_MIN = 1, VEL_MAX = 10, VEL_PADRAO = 4;
    const pixelsPorSegundo = nivel => 6 * Math.pow(1.28, nivel - 1);  // 1 ≈ 6 px/s ... 10 ≈ 55 px/s
    const ESCONDER_MENU_EM = 5000;
    let rolando = false, velocidade = VEL_PADRAO, posicao = 0, ultimoQuadro = 0, arrastando = false;
    let travaDaRolagem = false, esperaMenu = null;

    const chaveVelocidade = () => 'cifra-rolagem:' + (focada?.dataset.musica || 'geral');
    function carregarVelocidade() {
        const salva = parseInt(ler(chaveVelocidade(), ler('cifra-rolagem-ultima', String(VEL_PADRAO))), 10);
        velocidade = Math.min(VEL_MAX, Math.max(VEL_MIN, salva || VEL_PADRAO));
        mostrarVelocidade();
    }
    function mostrarVelocidade() {
        controles.querySelector('.foco-velocidade').textContent = `Vel. ${velocidade}`;
        controles.querySelector('[data-rolar="menos"]').disabled = velocidade <= VEL_MIN;
        controles.querySelector('[data-rolar="mais"]').disabled = velocidade >= VEL_MAX;
        const play = controles.querySelector('[data-rolar="play"]');
        play.innerHTML = rolando ? '<i class="bi bi-pause-fill"></i>' : '<i class="bi bi-play-fill"></i>';
        play.setAttribute('aria-label', rolando ? 'Pausar a rolagem' : 'Rolar a cifra');
    }
    function mudarVelocidade(passo) {
        velocidade = Math.min(VEL_MAX, Math.max(VEL_MIN, velocidade + passo));
        gravar(chaveVelocidade(), String(velocidade));
        gravar('cifra-rolagem-ultima', String(velocidade));  // ponto de partida para músicas novas
        mostrarVelocidade();
    }

    const noFim = el => el.scrollTop + el.clientHeight >= el.scrollHeight - 2;

    // O músico pode rolar à vontade (dedo, roda do mouse, barra) com o play ligado: a cada quadro,
    // se a tela não está onde a rolagem deixou, foi ele que mexeu -> a rolagem adota a nova posição.
    // Durante o toque e logo depois (embalo do dedo), a rolagem não empurra.
    let ultimoDefinido = 0, esperarAte = 0;
    const segurarRolagem = ms => { esperarAte = Math.max(esperarAte, performance.now() + ms); };

    function quadro(agora) {
        if (!rolando || !focada) return;
        const passou = Math.min(0.1, (agora - ultimoQuadro) / 1000);  // segundos (limita se a aba ficou parada)
        ultimoQuadro = agora;
        const atual = focada.scrollTop;
        if (Math.abs(atual - ultimoDefinido) > 1) {   // mexeram na rolagem: segue de onde está agora
            posicao = atual;
            segurarRolagem(600);
        }
        if (arrastando || agora < esperarAte) {
            posicao = atual;
        } else {
            const limite = focada.scrollHeight - focada.clientHeight;
            posicao = Math.min(limite, posicao + pixelsPorSegundo(velocidade) * passou);  // no fim, fica parada esperando
            focada.scrollTop = posicao;
        }
        ultimoDefinido = focada.scrollTop;
        // Chegou ao fim: o botão da próxima música fica em destaque (o menu não aparece sozinho)
        const fim = noFim(focada);
        const proxima = controles.querySelector('[data-foco-acao="proxima"]');
        proxima.classList.toggle('destaque', fim && !proxima.disabled && !proxima.hidden);
        requestAnimationFrame(quadro);
    }

    async function iniciarRolagem() {
        if (!focada || rolando) return;
        rolando = true;
        posicao = focada.scrollTop;
        ultimoDefinido = focada.scrollTop;
        esperarAte = 0;
        ultimoQuadro = performance.now();
        mostrarVelocidade();
        requestAnimationFrame(quadro);
        agendarEsconderMenu();
        if (!telaAcesa() && 'wakeLock' in navigator) {  // tela acesa enquanto rola
            try {
                trava = await navigator.wakeLock.request('screen');
                travaDaRolagem = true;
                trava.addEventListener('release', () => { trava = null; atualizarBotaoTela(); });
                atualizarBotaoTela();
            } catch (e) { /* sem suporte */ }
        }
    }

    function pararRolagem() {
        if (!rolando) return;
        rolando = false;
        controles.querySelector('[data-foco-acao="proxima"]').classList.remove('destaque');
        mostrarVelocidade();
        mostrarMenu();
        if (travaDaRolagem && trava) {
            trava.release().catch(() => {});
            trava = null;
            atualizarBotaoTela();
        }
        travaDaRolagem = false;
    }

    // Menu que some sozinho depois de alguns segundos (tocando ou não)
    function esconderMenu() {
        clearTimeout(esperaMenu);
        controles.classList.add('foco-controles-oculto');
    }
    function mostrarMenu() {
        controles.classList.remove('foco-controles-oculto');
        agendarEsconderMenu();
    }
    function agendarEsconderMenu() {
        clearTimeout(esperaMenu);
        if (focada) esperaMenu = setTimeout(esconderMenu, ESCONDER_MENU_EM);
    }

    // A rolagem só aparece quando a cifra passa da altura da tela
    function atualizarRolagemVisivel() {
        if (!focada) return;
        const rola = focada.scrollHeight > focada.clientHeight + 4;
        controles.querySelector('.foco-rolagem').hidden = !rola;
        if (!rola) pararRolagem();
    }

    controles.addEventListener('click', e => {
        const acao = e.target.closest('[data-rolar]')?.dataset.rolar;
        if (acao === 'play') (rolando ? pararRolagem() : iniciarRolagem());
        if (acao === 'menos') mudarVelocidade(-1);
        if (acao === 'mais') mudarVelocidade(1);
        mostrarMenu();
    });

    // A altura da cifra muda com A−/A+, acordes, desenhos ou girando o celular: confere se ainda rola
    document.addEventListener('click', () => { if (focada) setTimeout(atualizarRolagemVisivel, 80); });
    window.addEventListener('resize', () => { if (focada) setTimeout(atualizarRolagemVisivel, 250); });

    // Tocar na cifra (fora de botões e links): menu aparecendo -> some; menu escondido -> aparece
    document.addEventListener('click', e => {
        if (!focada || !focada.contains(e.target)) return;
        if (e.target.closest('button, a, select, input, label')) return;
        if (controles.classList.contains('foco-controles-oculto')) mostrarMenu();
        else esconderMenu();
    });

    // Arrastar a cifra com o dedo durante a rolagem: a posição segue o dedo e a rolagem continua dali
    const comecouArrastar = e => { if (focada && focada.contains(e.target)) arrastando = true; };
    const terminouArrastar = () => {
        if (!arrastando) return;
        arrastando = false;
        segurarRolagem(900);  // deixa o embalo do dedo terminar antes de voltar a rolar
    };
    document.addEventListener('touchstart', comecouArrastar, { passive: true });
    document.addEventListener('touchend', terminouArrastar, { passive: true });
    document.addEventListener('touchcancel', terminouArrastar, { passive: true });
    // Roda do mouse, barra de rolagem e teclado (computador)
    ['wheel', 'mousedown', 'keydown'].forEach(tipo => document.addEventListener(tipo, e => {
        if (focada && rolando && (tipo === 'keydown' || focada.contains(e.target))) segurarRolagem(600);
    }, { passive: true }));
    // Saiu do app/aba no meio da música: pausa (ao voltar, é só dar play de novo)
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') pararRolagem();
    });

    const secoesFoco = () => Array.from(document.querySelectorAll('[data-foco]'));

    function atualizarControles() {
        const lista = secoesFoco();
        const i = lista.indexOf(focada);
        const varias = lista.length > 1;
        controles.querySelector('[data-foco-acao="anterior"]').hidden = !varias;
        controles.querySelector('[data-foco-acao="proxima"]').hidden = !varias;
        controles.querySelector('[data-foco-acao="anterior"]').disabled = i <= 0;
        controles.querySelector('[data-foco-acao="proxima"]').disabled = i >= lista.length - 1;
        controles.querySelector('.foco-posicao').textContent = varias ? `${i + 1} de ${lista.length}` : '';
        aplicar();
        atualizarRolagemVisivel();
    }

    function abrirFoco(secao, telaCheia) {
        pararRolagem();
        if (focada) focada.classList.remove('em-foco');
        focada = secao;
        secao.classList.add('em-foco');
        document.body.classList.add('modo-foco');
        secao.scrollTop = 0;
        controles.hidden = false;
        controles.querySelector('[data-foco-acao="proxima"]').classList.remove('destaque');
        atualizarControles();
        carregarVelocidade();
        mostrarMenu();
        const raiz = document.documentElement;
        if (telaCheia && !document.fullscreenElement && raiz.requestFullscreen) {
            raiz.requestFullscreen().catch(() => { /* sem suporte: fica só a cobertura da página */ });
        }
    }

    function fecharFoco() {
        if (!focada) return;
        pararRolagem();
        const secao = focada;
        focada = null;
        secao.classList.remove('em-foco');
        document.body.classList.remove('modo-foco');
        controles.hidden = true;
        if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {});
        aplicar();  // a largura disponível mudou
        secao.scrollIntoView({ block: 'start' });
    }

    function mover(passo) {
        const lista = secoesFoco();
        const proxima = lista[lista.indexOf(focada) + passo];
        if (proxima) abrirFoco(proxima, false);
    }

    controles.addEventListener('click', e => {
        const acao = e.target.closest('[data-foco-acao]')?.dataset.focoAcao;
        if (acao === 'anterior') mover(-1);
        if (acao === 'proxima') mover(1);
        if (acao === 'fechar') fecharFoco();
    });
    document.addEventListener('keydown', e => {
        if (!focada) return;
        if (e.key === ' ') { e.preventDefault(); rolando ? pararRolagem() : iniciarRolagem(); }
        if (e.key === 'Escape') fecharFoco();
        if (e.key === 'ArrowRight') mover(1);
        if (e.key === 'ArrowLeft') mover(-1);
    });
    // Saiu da tela cheia pelo botão "voltar" ou Esc do navegador: fecha também o modo foco
    document.addEventListener('fullscreenchange', () => {
        if (!document.fullscreenElement && focada) fecharFoco();
    });

    if (!('wakeLock' in navigator)) {
        document.querySelectorAll('[data-cifra="tela"]').forEach(b => b.remove());
    }
    aplicar();
})();
