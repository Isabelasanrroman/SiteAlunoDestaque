let params = new URLSearchParams(window.location.search);

let id = params.get("id");

async function carregar() {

    let resposta =
    await fetch("/api/classificacao/" + id);

    let alunos = await resposta.json();

    let tbody =
    document.querySelector("#tabela tbody");

    alunos.forEach(a => {

        let tr = document.createElement("tr");

        tr.innerHTML = `
        <td>${a.nome}</td>
        <td>${a.media}</td>
        <td>${a.freq}</td>
        <td>${a.classificacao}</td>
        `;

        tbody.appendChild(tr);

    });
}

carregar();