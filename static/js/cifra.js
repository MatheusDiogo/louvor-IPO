// Leitor de cifras: tamanho da letra, mostrar/ocultar acordes, manter a tela acesa e troca de tom.
(function () {
    const ler = (chave, padrao) => {
        try { const v = localStorage.getItem(chave); return v === null ? padrao : v; } catch (e) { return padrao; }
    };
    const gravar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch (e) { /* sem armazenamento */ } };

    let escala = parseFloat(ler('cifra-escala', '1')) || 1;
    let acordes = ler('cifra-acordes', '1') === '1';

    function aplicar() {
        document.querySelectorAll('.cifra-leitor').forEach(el => {
            el.style.setProperty('--cifra-escala', escala);
            el.classList.toggle('sem-acordes', !acordes);
        });
        document.querySelectorAll('[data-cifra="acordes"]').forEach(b => b.classList.toggle('ativo', acordes));
    }

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

    document.addEventListener('click', e => {
        const botao = e.target.closest('[data-cifra]');
        if (!botao) return;
        const acao = botao.dataset.cifra;
        if (acao === 'foco') {
            const alvo = botao.dataset.focoAlvo ? document.querySelector(botao.dataset.focoAlvo) : botao.closest('[data-foco]');
            if (alvo) abrirFoco(alvo, true);
            return;
        }
        if (acao === 'menor') escala = Math.max(0.7, +(escala - 0.1).toFixed(2));
        if (acao === 'maior') escala = Math.min(2, +(escala + 0.1).toFixed(2));
        if (acao === 'acordes') acordes = !acordes;
        if (acao === 'tela') {
            alternarTela(botao).then(() => gravar('cifra-tela', telaAcesa() ? '1' : '0'));
            return;
        }
        gravar('cifra-escala', escala);
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
        <button type="button" class="btn btn-light border" data-foco-acao="anterior" aria-label="Música anterior"><i class="bi bi-chevron-left"></i></button>
        <span class="foco-posicao small fw-semibold text-truncate"></span>
        <button type="button" class="btn btn-light border" data-foco-acao="proxima" aria-label="Próxima música"><i class="bi bi-chevron-right"></i></button>
        <span class="foco-separador"></span>
        <button type="button" class="btn btn-light border" data-cifra="menor" aria-label="Diminuir letra">A−</button>
        <button type="button" class="btn btn-light border" data-cifra="maior" aria-label="Aumentar letra">A+</button>
        <button type="button" class="btn btn-light border" data-cifra="acordes" aria-label="Mostrar/ocultar acordes"><i class="bi bi-music-note-beamed"></i></button>
        <button type="button" class="btn btn-success" data-foco-acao="fechar" aria-label="Sair da tela cheia"><i class="bi bi-x-lg"></i></button>`;
    document.body.appendChild(controles);

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
    }

    function abrirFoco(secao, telaCheia) {
        if (focada) focada.classList.remove('em-foco');
        focada = secao;
        secao.classList.add('em-foco');
        document.body.classList.add('modo-foco');
        secao.scrollTop = 0;
        controles.hidden = false;
        atualizarControles();
        const raiz = document.documentElement;
        if (telaCheia && !document.fullscreenElement && raiz.requestFullscreen) {
            raiz.requestFullscreen().catch(() => { /* sem suporte: fica só a cobertura da página */ });
        }
    }

    function fecharFoco() {
        if (!focada) return;
        const secao = focada;
        focada = null;
        secao.classList.remove('em-foco');
        document.body.classList.remove('modo-foco');
        controles.hidden = true;
        if (document.fullscreenElement && document.exitFullscreen) document.exitFullscreen().catch(() => {});
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
