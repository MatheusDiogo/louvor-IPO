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

    if (!('wakeLock' in navigator)) {
        document.querySelectorAll('[data-cifra="tela"]').forEach(b => b.remove());
    }
    aplicar();
})();
