// Desenhos (diagramas) dos acordes de violão em cima de cada cifra.
// Os dados vêm do servidor (apps/musicas/acordes.py) dentro da própria página, então funciona sem internet.
// Tocar num desenho passa para a próxima posição ("Variar"); a escolha fica guardada no aparelho.
(function () {
    const faixas = document.querySelectorAll('.acordes-faixa[data-diagramas]');
    const botoes = document.querySelectorAll('[data-diagramas-botao]');
    if (!faixas.length) return;

    const ler = (chave, padrao) => {
        try { const v = localStorage.getItem(chave); return v === null ? padrao : v; } catch (e) { return padrao; }
    };
    const gravar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch (e) { /* sem armazenamento */ } };

    const NS = 'http://www.w3.org/2000/svg';
    const CORDAS = 6, CASAS_VISIVEIS = 4;
    const DX = 11, DY = 14, ESQ = 16, TOPO = 8;           // espaço entre cordas / casas e margens
    const LARGURA = ESQ + DX * (CORDAS - 1) + 8;
    const ALTURA = TOPO + DY * CASAS_VISIVEIS + 16;

    function el(nome, atributos, texto) {
        const e = document.createElementNS(NS, nome);
        Object.entries(atributos).forEach(([k, v]) => e.setAttribute(k, v));
        if (texto !== undefined) e.textContent = texto;
        return e;
    }

    // Desenha um acorde: casas (6ª -> 1ª corda, -1 = não toca), dedos e pestanas
    function desenhar(desenho) {
        const { casas, dedos = [], pestanas = [] } = desenho;
        const apertadas = casas.filter(c => c > 0);
        const maior = apertadas.length ? Math.max(...apertadas) : 0;
        const menor = apertadas.length ? Math.min(...apertadas) : 1;
        const inicio = maior <= CASAS_VISIVEIS ? 1 : menor;  // primeira casa mostrada
        const x = corda => ESQ + corda * DX;
        const y = casa => TOPO + (casa - inicio + 0.5) * DY;

        const svg = el('svg', { viewBox: `0 0 ${LARGURA} ${ALTURA}`, width: LARGURA, height: ALTURA,
                                class: 'acorde-svg', 'aria-hidden': 'true' });
        // casas (linhas horizontais) e cordas (verticais)
        for (let i = 0; i <= CASAS_VISIVEIS; i++) {
            svg.appendChild(el('line', { x1: x(0), x2: x(CORDAS - 1), y1: TOPO + i * DY, y2: TOPO + i * DY,
                                         class: i === 0 && inicio === 1 ? 'acorde-pestana-fixa' : 'acorde-traste' }));
        }
        for (let c = 0; c < CORDAS; c++) {
            svg.appendChild(el('line', { x1: x(c), x2: x(c), y1: TOPO, y2: TOPO + CASAS_VISIVEIS * DY, class: 'acorde-corda' }));
        }
        if (inicio > 1) {
            svg.appendChild(el('text', { x: ESQ - 9, y: TOPO + DY * 0.5 + 3.5, class: 'acorde-casa-inicial' }, inicio));
        }
        // pestanas: barra da primeira à última corda apertada naquela casa
        const naPestana = new Set();
        pestanas.forEach(casa => {
            const cordas = casas.map((c, i) => (c === casa ? i : -1)).filter(i => i >= 0);
            if (cordas.length < 2) return;
            const ini = Math.min(...cordas), fim = Math.max(...cordas);
            for (let i = ini; i <= fim; i++) if (casas[i] === casa) naPestana.add(i);
            svg.appendChild(el('rect', { x: x(ini) - 4.5, y: y(casa) - 4.5, width: x(fim) - x(ini) + 9, height: 9,
                                         rx: 4.5, class: 'acorde-dedo' }));
        });
        // dedos
        casas.forEach((casa, corda) => {
            if (casa <= 0 || naPestana.has(corda)) return;
            svg.appendChild(el('circle', { cx: x(corda), cy: y(casa), r: 4.8, class: 'acorde-dedo' }));
            if (dedos[corda]) {
                svg.appendChild(el('text', { x: x(corda), y: y(casa) + 2.6, class: 'acorde-dedo-num' }, dedos[corda]));
            }
        });
        // embaixo: × = não toca, ○ = corda solta
        casas.forEach((casa, corda) => {
            const yy = TOPO + CASAS_VISIVEIS * DY + 10;
            if (casa < 0) svg.appendChild(el('text', { x: x(corda), y: yy, class: 'acorde-marca' }, '×'));
            if (casa === 0) svg.appendChild(el('circle', { cx: x(corda), cy: yy - 3, r: 2.6, class: 'acorde-solta' }));
        });
        return svg;
    }

    function cartao(acorde) {
        const item = document.createElement('div');
        item.className = 'acorde-item';
        item.setAttribute('role', 'listitem');
        const nome = document.createElement('div');
        nome.className = 'acorde-nome';
        nome.textContent = acorde.nome;
        item.appendChild(nome);

        if (!acorde.desenhos.length) {
            const vazio = document.createElement('div');
            vazio.className = 'acorde-vazio';
            vazio.textContent = 'sem desenho';
            item.appendChild(vazio);
            return item;
        }

        const chave = 'acorde-variacao:' + acorde.nome;
        let atual = Math.min(parseInt(ler(chave, '0'), 10) || 0, acorde.desenhos.length - 1);
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'acorde-botao';
        const rodape = document.createElement('div');
        rodape.className = 'acorde-variar';

        const mostrar = () => {
            const desenho = acorde.desenhos[atual];
            botao.replaceChildren(desenhar(desenho));
            const total = acorde.desenhos.length;
            const partes = [];
            if (total > 1) partes.push(`${atual + 1}/${total}`, 'Variar');
            if (desenho.gerado) partes.push('auto');
            rodape.textContent = partes.join(' · ');
            botao.classList.toggle('gerado', !!desenho.gerado);
            botao.title = total > 1 ? `${acorde.nome}: toque para ver outra posição` : acorde.nome;
            botao.setAttribute('aria-label', `${acorde.nome}, posição ${atual + 1} de ${total}`);
        };
        botao.addEventListener('click', () => {
            if (acorde.desenhos.length < 2) return;
            atual = (atual + 1) % acorde.desenhos.length;
            gravar(chave, String(atual));
            // atualiza o mesmo acorde nas outras músicas da página
            document.querySelectorAll('.acorde-item').forEach(outro => {
                if (outro !== item && outro.dataset.nome === acorde.nome && outro.variar) outro.variar(atual);
            });
            mostrar();
        });
        item.dataset.nome = acorde.nome;
        item.variar = indice => { atual = Math.min(indice, acorde.desenhos.length - 1); mostrar(); };
        item.appendChild(botao);
        item.appendChild(rodape);
        if (acorde.aviso) {
            const aviso = document.createElement('div');
            aviso.className = 'acorde-aviso';
            aviso.textContent = acorde.aviso;
            item.appendChild(aviso);
        }
        mostrar();
        return item;
    }

    faixas.forEach(faixa => {
        let lista = [];
        try { lista = JSON.parse(document.getElementById(faixa.dataset.diagramas).textContent); } catch (e) { /* sem dados */ }
        lista.forEach(acorde => faixa.appendChild(cartao(acorde)));
    });

    // "Desenhos dos acordes": abrir/fechar (vale para todas as músicas e fica guardado no aparelho)
    let visiveis = ler('cifra-diagramas', '1') === '1';
    const aplicar = () => {
        document.querySelectorAll('.cifra-leitor').forEach(l => l.classList.toggle('sem-diagramas', !visiveis));
        botoes.forEach(b => b.setAttribute('aria-expanded', visiveis ? 'true' : 'false'));
    };
    botoes.forEach(b => {
        b.addEventListener('click', () => {
            visiveis = !visiveis;
            gravar('cifra-diagramas', visiveis ? '1' : '0');
            aplicar();
        });
    });
    aplicar();
})();
