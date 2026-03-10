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