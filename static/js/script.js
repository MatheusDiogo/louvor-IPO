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
    abrirModal("modalInstrumento");
}

function editarInstrumento(btn) {
    document.getElementById("instrumento_id").value = btn.dataset.id;
    document.getElementById("instrumento_nome").value = btn.dataset.nome;
    document.getElementById("instrumento_ordem").value = btn.dataset.ordem;
    abrirModal("modalInstrumento");
}

/* ---------- Músicas ---------- */

function novaMusica() {
    document.getElementById("musica_id").value = "";
    document.getElementById("musica_nome").value = "";
    document.getElementById("musica_youtube").value = "";
    document.getElementById("modalMusicaTitulo").innerHTML = '<i class="bi bi-plus-circle me-2"></i>Nova Música';
    abrirModal("modalMusica");
}

function editarMusica(btn) {
    document.getElementById("musica_id").value = btn.dataset.id;
    document.getElementById("musica_nome").value = btn.dataset.nome;
    document.getElementById("musica_youtube").value = btn.dataset.youtube || "";
    document.getElementById("modalMusicaTitulo").innerHTML = '<i class="bi bi-pencil-square me-2"></i>Editar Música';
    abrirModal("modalMusica");
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
