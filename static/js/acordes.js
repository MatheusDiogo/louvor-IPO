// Desenhos dos acordes em cima de cada cifra: violão ou teclado.
// Os dados vêm do servidor (apps/musicas/acordes.py) dentro da própria página, então funciona sem internet.
//
// Qual instrumento aparece:
//   1. nas cifras do culto, o instrumento em que a pessoa está escalada (definido no cadastro do instrumento);
//   2. senão, a última escolha feita no seletor (guardada no aparelho);
//   3. senão, o primeiro instrumento do cadastro da pessoa; senão, violão.
// Escalado num instrumento com "Nenhum" (ex.: voz): os desenhos começam fechados.
(function () {
    const blocos = document.querySelectorAll('.acordes-bloco');

    const ler = (chave, padrao) => {
        try { const v = localStorage.getItem(chave); return v === null ? padrao : v; } catch (e) { return padrao; }
    };
    const gravar = (chave, valor) => { try { localStorage.setItem(chave, valor); } catch (e) { /* sem armazenamento */ } };

    const INSTRUMENTOS = ['violao', 'teclado'];
    const NS = 'http://www.w3.org/2000/svg';
    const SUSTENIDOS = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'];
    const BEMOIS = ['C', 'Db', 'D', 'Eb', 'E', 'F', 'Gb', 'G', 'Ab', 'A', 'Bb', 'B'];
    // Nome da nota com sustenido ou bemol, conforme o nome do acorde ("Bb", "Eb/G" usam bemol)
    const nomeNota = (nota, acorde) => (/^[A-G]b|\/[A-G]b/.test(acorde) ? BEMOIS : SUSTENIDOS)[nota];

    function el(nome, atributos, texto) {
        const e = document.createElementNS(NS, nome);
        Object.entries(atributos).forEach(([k, v]) => e.setAttribute(k, v));
        if (texto !== undefined) e.textContent = texto;
        return e;
    }

    // ------------------------------------------------------------ braço do violão
    // marcas: [{corda, casa, texto}] (dedos apertados); embaixo: valor por corda (-1 = ×, 0 = ○, null = nada)
    function braco({ cordas, inicio, visiveis, marcas, pestanas = [], embaixo = [] }) {
        const DX = 11, DY = 14, ESQ = 16, TOPO = 8;
        const largura = ESQ + DX * (cordas - 1) + 8, altura = TOPO + DY * visiveis + 16;
        const x = corda => ESQ + corda * DX;
        const y = casa => TOPO + (casa - inicio + 0.5) * DY;
        const svg = el('svg', { viewBox: `0 0 ${largura} ${altura}`, width: largura, height: altura,
                                class: 'acorde-svg', 'aria-hidden': 'true' });
        for (let i = 0; i <= visiveis; i++) {
            svg.appendChild(el('line', { x1: x(0), x2: x(cordas - 1), y1: TOPO + i * DY, y2: TOPO + i * DY,
                                         class: i === 0 && inicio === 1 ? 'acorde-pestana-fixa' : 'acorde-traste' }));
        }
        for (let c = 0; c < cordas; c++) {
            svg.appendChild(el('line', { x1: x(c), x2: x(c), y1: TOPO, y2: TOPO + visiveis * DY, class: 'acorde-corda' }));
        }
        if (inicio > 1) svg.appendChild(el('text', { x: ESQ - 9, y: TOPO + DY * 0.5 + 3.5, class: 'acorde-casa-inicial' }, inicio));
        pestanas.forEach(({ casa, de, ate }) => {
            svg.appendChild(el('rect', { x: x(de) - 4.5, y: y(casa) - 4.5, width: x(ate) - x(de) + 9, height: 9,
                                         rx: 4.5, class: 'acorde-dedo' }));
        });
        marcas.forEach(({ corda, casa, texto }) => {
            svg.appendChild(el('circle', { cx: x(corda), cy: y(casa), r: 4.8, class: 'acorde-dedo' }));
            if (texto) svg.appendChild(el('text', { x: x(corda), y: y(casa) + 2.6, class: 'acorde-dedo-num' }, texto));
        });
        embaixo.forEach((valor, corda) => {
            const yy = TOPO + visiveis * DY + 10;
            if (valor < 0) svg.appendChild(el('text', { x: x(corda), y: yy, class: 'acorde-marca' }, '×'));
            if (valor === 0) svg.appendChild(el('circle', { cx: x(corda), cy: yy - 3, r: 2.6, class: 'acorde-solta' }));
        });
        return svg;
    }

    // Violão: casas (6ª -> 1ª corda, -1 = não toca), dedos e pestanas
    function desenhoViolao(desenho) {
        const { casas, dedos = [], pestanas = [] } = desenho;
        const apertadas = casas.filter(c => c > 0);
        const maior = apertadas.length ? Math.max(...apertadas) : 0;
        const inicio = maior <= 4 ? 1 : Math.min(...apertadas);
        const naPestana = new Set();
        const barras = [];
        pestanas.forEach(casa => {
            const cordas = casas.map((c, i) => (c === casa ? i : -1)).filter(i => i >= 0);
            if (cordas.length < 2) return;
            const de = Math.min(...cordas), ate = Math.max(...cordas);
            for (let i = de; i <= ate; i++) if (casas[i] === casa) naPestana.add(i);
            barras.push({ casa, de, ate });
        });
        const marcas = casas.map((casa, corda) => ({ corda, casa, texto: dedos[corda] || '' }))
            .filter(m => m.casa > 0 && !naPestana.has(m.corda));
        return braco({ cordas: 6, inicio, visiveis: 4, marcas, pestanas: barras, embaixo: casas.map(c => (c > 0 ? null : c)) });
    }

    // Teclado: duas oitavas. Mão esquerda (1ª oitava) = baixo; mão direita (2ª oitava) = notas do acorde.
    const BRANCAS = [0, 2, 4, 5, 7, 9, 11];
    const PRETAS = { 1: 0, 3: 1, 6: 3, 8: 4, 10: 5 };  // nota -> branca à esquerda
    function desenhoTeclado(acorde) {
        const W = 8, H = 40, PW = 5.2, PH = 25, OITAVAS = 2;
        const largura = W * 7 * OITAVAS + 2, altura = H + 2;
        const svg = el('svg', { viewBox: `0 0 ${largura} ${altura}`, width: largura, height: altura,
                                class: 'acorde-svg acorde-teclado', 'aria-hidden': 'true' });
        const marcadas = new Map();  // posição (0-23) -> classe
        marcadas.set(acorde.baixo, 'tecla-baixo');
        acorde.notas.forEach(n => marcadas.set(12 + n, 'tecla-acorde'));
        for (let o = 0; o < OITAVAS; o++) {
            BRANCAS.forEach((nota, i) => {
                const pos = o * 12 + nota;
                svg.appendChild(el('rect', { x: 1 + (o * 7 + i) * W, y: 1, width: W, height: H, rx: 1.5,
                                             class: 'tecla-branca ' + (marcadas.get(pos) || '') }));
            });
        }
        for (let o = 0; o < OITAVAS; o++) {
            Object.entries(PRETAS).forEach(([nota, branca]) => {
                const pos = o * 12 + Number(nota);
                svg.appendChild(el('rect', { x: 1 + (o * 7 + branca + 1) * W - PW / 2, y: 1, width: PW, height: PH, rx: 1,
                                             class: 'tecla-preta ' + (marcadas.get(pos) || '') }));
            });
        }
        return svg;
    }

    // ------------------------------------------------------------ cartões
    function cartao(acorde, instrumento) {
        const item = document.createElement('div');
        item.className = 'acorde-item acorde-' + instrumento;
        item.setAttribute('role', 'listitem');
        item.dataset.nome = acorde.nome;
        const nome = document.createElement('div');
        nome.className = 'acorde-nome';
        nome.textContent = acorde.nome;
        item.appendChild(nome);

        const temNotas = Array.isArray(acorde.notas) && acorde.notas.length && acorde.baixo !== null && acorde.baixo !== undefined;
        const semDesenho = texto => {
            const vazio = document.createElement('div');
            vazio.className = 'acorde-vazio';
            vazio.textContent = texto;
            item.appendChild(vazio);
            return item;
        };

        let opcoes;   // lista de variações (o que o "Variar" percorre)
        let desenhar; // índice -> svg
        let legenda = () => '';
        if (instrumento === 'violao') {
            if (!acorde.desenhos || !acorde.desenhos.length) return semDesenho('sem desenho');
            opcoes = acorde.desenhos;
            desenhar = i => desenhoViolao(opcoes[i]);
        } else {
            if (!temNotas || acorde.tipo_conhecido === false) return semDesenho('sem desenho');
            opcoes = [0];
            desenhar = () => desenhoTeclado(acorde);
            legenda = () => {
                const notas = acorde.notas.map(n => nomeNota(n, acorde.nome)).join(' ');
                return acorde.baixo !== acorde.notas[0] ? `${nomeNota(acorde.baixo, acorde.nome)} | ${notas}` : notas;
            };
        }

        const chave = `acorde-variacao:${instrumento}:${acorde.nome}`;
        let atual = Math.min(parseInt(ler(chave, instrumento === 'violao' ? ler('acorde-variacao:' + acorde.nome, '0') : '0'), 10) || 0,
                             opcoes.length - 1);
        const botao = document.createElement('button');
        botao.type = 'button';
        botao.className = 'acorde-botao';
        const rodape = document.createElement('div');
        rodape.className = 'acorde-variar';

        const mostrar = () => {
            botao.replaceChildren(desenhar(atual));
            const partes = [];
            const texto = legenda();
            if (texto) partes.push(texto);
            if (opcoes.length > 1) partes.push(`${atual + 1}/${opcoes.length}`, 'Variar');
            const gerado = instrumento === 'violao' && opcoes[atual].gerado;
            if (gerado) partes.push('auto');
            rodape.textContent = partes.join(' · ');
            botao.classList.toggle('gerado', !!gerado);
            botao.title = opcoes.length > 1 ? `${acorde.nome}: toque para ver outra posição` : acorde.nome;
            botao.setAttribute('aria-label', `${acorde.nome}, posição ${atual + 1} de ${opcoes.length}`);
        };
        botao.addEventListener('click', () => {
            if (opcoes.length < 2) return;
            atual = (atual + 1) % opcoes.length;
            gravar(chave, String(atual));
            // o mesmo acorde nas outras músicas da página acompanha
            document.querySelectorAll(`.acorde-${instrumento}`).forEach(outro => {
                if (outro !== item && outro.dataset.nome === acorde.nome && outro.variar) outro.variar(atual);
            });
            mostrar();
        });
        item.variar = indice => { atual = Math.min(indice, opcoes.length - 1); mostrar(); };
        item.appendChild(botao);
        item.appendChild(rodape);
        if (instrumento === 'violao' && acorde.aviso) {
            const aviso = document.createElement('div');
            aviso.className = 'acorde-aviso';
            aviso.textContent = acorde.aviso;
            item.appendChild(aviso);
        }
        mostrar();
        return item;
    }

    // Usado também pela tela de cadastro de acordes (líderes)
    window.DesenhosAcordes = { violao: desenhoViolao };

    // ------------------------------------------------------------ montagem
    if (!blocos.length) return;
    const primeiro = blocos[0].dataset;
    const doCulto = INSTRUMENTOS.includes(primeiro.desenhoEscala) ? primeiro.desenhoEscala : '';
    const salvo = ler('cifra-instrumento', '');
    let instrumento = doCulto || (INSTRUMENTOS.includes(salvo) ? salvo : '') ||
                      (INSTRUMENTOS.includes(primeiro.desenhoPadrao) ? primeiro.desenhoPadrao : '') || 'violao';

    const dados = new Map();
    blocos.forEach(bloco => {
        const faixa = bloco.querySelector('.acordes-faixa');
        let lista = [];
        try { lista = JSON.parse(document.getElementById(faixa.dataset.diagramas).textContent); } catch (e) { /* sem dados */ }
        dados.set(bloco, lista);
    });

    function montar() {
        blocos.forEach(bloco => {
            const faixa = bloco.querySelector('.acordes-faixa');
            faixa.replaceChildren(...dados.get(bloco).map(acorde => cartao(acorde, instrumento)));
            bloco.querySelectorAll('[data-instrumento]').forEach(b => {
                const ativo = b.dataset.instrumento === instrumento;
                b.classList.toggle('btn-success', ativo);
                b.classList.toggle('btn-light', !ativo);
                b.setAttribute('aria-pressed', ativo ? 'true' : 'false');
            });
        });
    }

    document.addEventListener('click', e => {
        const botao = e.target.closest('.acordes-bloco [data-instrumento]');
        if (!botao) return;
        instrumento = botao.dataset.instrumento;
        gravar('cifra-instrumento', instrumento);
        montar();
    });

    // Abrir/fechar (vale para todas as músicas e fica guardado no aparelho).
    // Escalado num instrumento sem desenho (ex.: voz): começa fechado nesta página.
    let visiveis = primeiro.desenhoEscala === 'nenhum' ? false : ler('cifra-diagramas', '1') === '1';
    const aplicarVisibilidade = () => {
        document.querySelectorAll('.cifra-leitor').forEach(l => l.classList.toggle('sem-diagramas', !visiveis));
        document.querySelectorAll('[data-diagramas-botao]').forEach(b => b.setAttribute('aria-expanded', visiveis ? 'true' : 'false'));
    };
    document.querySelectorAll('[data-diagramas-botao]').forEach(b => b.addEventListener('click', () => {
        visiveis = !visiveis;
        gravar('cifra-diagramas', visiveis ? '1' : '0');
        aplicarVisibilidade();
    }));

    montar();
    aplicarVisibilidade();
})();
