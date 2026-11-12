// Mostrar/ocultar senha (páginas de login e redefinição)
function togglePassword(inputId, icon) {
    const input = document.getElementById(inputId || "password");
    if (!input) return;
    const mostrar = input.type === "password";
    input.type = mostrar ? "text" : "password";
    if (icon) {
        icon.classList.toggle("bi-eye", !mostrar);
        icon.classList.toggle("bi-eye-slash", mostrar);
    }
}

// Abre um modal do Bootstrap (se o Bootstrap estiver carregado na página)
function abrirModal(id) {
    const el = document.getElementById(id);
    if (!el || typeof bootstrap === "undefined") return;
    bootstrap.Modal.getOrCreateInstance(el).show();
}

/* ---------- Instrumentos ---------- */

function novoInstrumento() {
    document.getElementById("instrumento_id").value = "";
    document.getElementById("instrumento_nome").value = "";
    document.getElementById("instrumento_ordem").value = "";
    document.getElementById("instrumento_desenho").value = "";
    abrirModal("modalInstrumento");
}

function editarInstrumento(btn) {
    document.getElementById("instrumento_id").value = btn.dataset.id;
    document.getElementById("instrumento_nome").value = btn.dataset.nome;
    document.getElementById("instrumento_ordem").value = btn.dataset.ordem;
    document.getElementById("instrumento_desenho").value = btn.dataset.desenho || "";
    abrirModal("modalInstrumento");
}

/* ---------- Integrantes ---------- */

function novoIntegrante() {
    const form = document.querySelector("#modalIntegrante form");
    form.reset();
    document.getElementById("inst_id").value = "";
    document.getElementById("modalIntegranteTitulo").textContent = "Novo Integrante";
    abrirModal("modalIntegrante");
}

function editarIntegrante(btn) {
    const d = btn.dataset;
    document.querySelector("#modalIntegrante form").reset();
    document.getElementById("inst_id").value = d.id;
    document.getElementById("inst_nome").value = d.nome;
    document.getElementById("inst_sobrenome").value = d.sobrenome;
    document.getElementById("inst_email").value = d.email;
    document.getElementById("inst_lider").checked = d.lider === "1";

    const ids = (d.instrumentos || "").split(",").filter(Boolean);
    document.querySelectorAll("#modalIntegrante input[name='instrumentos']").forEach(cb => {
        cb.checked = ids.includes(cb.value);
    });

    document.getElementById("modalIntegranteTitulo").textContent = "Editar Integrante";
    abrirModal("modalIntegrante");
}

/* ---------- App (PWA): aviso sem internet e páginas guardadas ---------- */

(function () {
    const aviso = document.getElementById('avisoOffline');
    const atualizarAviso = () => { if (aviso) aviso.hidden = navigator.onLine; };
    window.addEventListener('online', atualizarAviso);
    window.addEventListener('offline', atualizarAviso);
    atualizarAviso();

    // Pede ao app para guardar as cifras dos próximos cultos (para abrir mesmo sem internet)
    const dados = document.getElementById('urlsOffline');
    if (!dados || !('serviceWorker' in navigator) || !navigator.onLine) return;
    const conexao = navigator.connection || {};
    if (conexao.saveData) return;  // modo de economia de dados ligado
    const urls = JSON.parse(dados.textContent);
    navigator.serviceWorker.ready.then(registro => {
        if (registro.active) registro.active.postMessage({ tipo: 'guardar', urls });
    });
})();
