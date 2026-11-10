document.addEventListener("DOMContentLoaded", () => {
    const buscador = document.querySelector("#busqueda");
    const formularioBusqueda = document.querySelector(".busqueda");
    const tarjetas = [...document.querySelectorAll(".producto-card")];
    const filtros = [...document.querySelectorAll(".categoria-filtro")];
    const contador = document.querySelector("#contador-productos");
    const sinResultados = document.querySelector(".sin-resultados");
    let categoriaActiva = "todas";

    const normalizar = (texto) => texto.toLocaleLowerCase("es").normalize("NFD").replace(/[\u0300-\u036f]/g, "");

    const actualizarCatalogo = () => {
        const texto = normalizar(buscador ? buscador.value : "");
        let visibles = 0;

        tarjetas.forEach((tarjeta) => {
            const coincideCategoria = categoriaActiva === "todas" || tarjeta.dataset.categoria === categoriaActiva;
            const coincideTexto = !texto || normalizar(tarjeta.dataset.nombre).includes(texto);
            const mostrar = coincideCategoria && coincideTexto;
            tarjeta.hidden = !mostrar;
            if (mostrar) visibles += 1;
        });

        if (contador) contador.textContent = visibles;
        if (sinResultados) sinResultados.hidden = visibles !== 0;
    };

    filtros.forEach((filtro) => {
        filtro.addEventListener("click", () => {
            categoriaActiva = filtro.dataset.categoria;
            filtros.forEach((item) => item.classList.toggle("activo", item === filtro));
            actualizarCatalogo();
            document.querySelector("#productos")?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
    });

    buscador?.addEventListener("input", actualizarCatalogo);
    formularioBusqueda?.addEventListener("submit", (evento) => {
        evento.preventDefault();
        actualizarCatalogo();
        document.querySelector("#productos")?.scrollIntoView({ behavior: "smooth", block: "start" });
    });

    actualizarCatalogo();
});
