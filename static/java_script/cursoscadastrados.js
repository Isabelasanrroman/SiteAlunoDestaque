async function carregarTurmas() {

    let resposta = await fetch("/api/turmas");

    let turmas = await resposta.json();

    let div = document.getElementById("listaTurmas");

    div.innerHTML = "";

    turmas.forEach(t => {

        let btn = document.createElement("button");

        btn.innerText = t.nome;

        btn.onclick = () => {

            window.location.href =
            "/classificacao?id=" + t.id;

        };

        div.appendChild(btn);

    });
}

carregarTurmas();