function togglePassword() {

    const input = document.getElementById("password");

    if (input.type === "password") {
        input.type = "text";
    } else {
        input.type = "password";
    }

}

document.addEventListener("DOMContentLoaded", function(){

    setTimeout(() => {

        const alert = document.querySelector(".login-error");

        if(alert){

            alert.style.transition = "opacity 0.5s";
            alert.style.opacity = "0";

            setTimeout(() => {
                alert.remove();
            }, 500);

        }

    }, 3000);

});

function novoInstrumento(){

    document.getElementById("instrumento_id").value = "";
    document.getElementById("instrumento_nome").value = "";

    new bootstrap.Modal(document.getElementById("modalInstrumento")).show();
}


function editarInstrumento(id,nome){

    document.getElementById("instrumento_id").value = id;
    document.getElementById("instrumento_nome").value = nome;

    new bootstrap.Modal(document.getElementById("modalInstrumento")).show();
}

// Inicializa o modal do Bootstrap
let modalMusicaElement = document.getElementById('modalMusica');
let modalMusica = new bootstrap.Modal(modalMusicaElement);

// Função para abrir o modal para uma NOVA música (limpa os campos)
function novaMusica() {
    document.getElementById('musica_id').value = '';
    document.getElementById('musica_nome').value = '';
    document.getElementById('musica_youtube').value = '';
    
    // Altera o título do modal se desejar
    modalMusicaElement.querySelector('.modal-title')?.innerText || 
    (modalMusicaElement.querySelector('h5').innerHTML = '<i class="bi bi-plus-circle me-2"></i>Nova Música');
    
    modalMusica.show();
}

// Função para abrir o modal para EDITAR (preenche os campos)
function editarMusica(id, nome, youtube) {
    document.getElementById('musica_id').value = id;
    document.getElementById('musica_nome').value = nome;
    document.getElementById('musica_youtube').value = youtube === 'None' ? '' : youtube;

    modalMusicaElement.querySelector('h5').innerHTML = '<i class="bi bi-pencil-square me-2"></i>Editar Música';
    
    modalMusica.show();
}

function editarIntegrante(id, nome, sobrenome, email, isLider, instrumentos) {
    // 1. Abre o modal manualmente (caso o data-bs-toggle falhe)
    const modal = new bootstrap.Modal(document.getElementById('modalIntegrante'));
    
    // 2. Preenche os campos de texto
    document.getElementById('inst_id').value = id;
    document.getElementById('inst_nome').value = nome;
    document.getElementById('inst_sobrenome').value = sobrenome;
    document.getElementById('inst_email').value = email;
    // O username geralmente é o email no seu caso
    if(document.getElementById('inst_username')) {
        document.getElementById('inst_username').value = email;
    }

    // 3. Preenche o select múltiplo de instrumentos
    const selectInstrumentos = document.getElementById('inst_instrumentos');
    const listaInstrumentos = instrumentos.split(','); // Transforma a string em array

    // Reseta seleções anteriores
    Array.from(selectInstrumentos.options).forEach(option => {
        option.selected = false;
    });

    // Marca como selecionado os instrumentos que o integrante já possui
    Array.from(selectInstrumentos.options).forEach(option => {
        if (listaInstrumentos.includes(option.text)) {
            option.selected = true;
        }
    });

    modal.show();
}

function limparFormulario() {
    document.getElementById('inst_id').value = '';
    document.querySelector('#modalIntegrante form').reset();
}