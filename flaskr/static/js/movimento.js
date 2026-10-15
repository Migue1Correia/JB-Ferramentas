// Movimento da interface: barra de progresso ao trocar de página, estado "enviando" nos
// formulários e esqueleto enquanto fotos e gráficos carregam. O visual fica no movimento.css.
(function () {
    var barra = document.createElement('div');
    barra.className = 'barra-progresso';
    barra.setAttribute('aria-hidden', 'true');
    document.body.appendChild(barra);

    var espera;
    function iniciarProgresso() {
        // Só aparece se a página demorar: em troca rápida a barra piscando atrapalharia
        clearTimeout(espera);
        espera = setTimeout(function () { barra.classList.add('ativa'); }, 150);
    }

    document.addEventListener('click', function (evento) {
        var link = evento.target.closest ? evento.target.closest('a[href]') : null;
        if (!link || evento.defaultPrevented || evento.button !== 0) return;
        if (evento.ctrlKey || evento.metaKey || evento.shiftKey || link.target === '_blank') return;
        if (link.origin !== location.origin || link.protocol.indexOf('http') !== 0) return;  // fora do site, ou "javascript:"
        if (link.pathname === location.pathname && link.hash) return;                        // âncora na mesma página
        iniciarProgresso();
    });

    document.addEventListener('submit', function (evento) {
        if (evento.defaultPrevented) return;  // o usuário cancelou uma confirmação
        var formulario = evento.target;
        if (formulario.dataset.enviando) {    // segundo clique enquanto o primeiro ainda está indo
            evento.preventDefault();
            return;
        }
        formulario.dataset.enviando = '1';
        formulario.classList.add('enviando');
        if (evento.submitter) evento.submitter.classList.add('girando');
        iniciarProgresso();
    });

    // Ao voltar pelo botão do navegador a página reaparece como estava: desfaz o estado "enviando"
    window.addEventListener('pageshow', function () {
        clearTimeout(espera);
        barra.classList.remove('ativa');
        document.querySelectorAll('form.enviando').forEach(function (formulario) {
            formulario.classList.remove('enviando');
            delete formulario.dataset.enviando;
        });
        document.querySelectorAll('.girando').forEach(function (botao) { botao.classList.remove('girando'); });
    });

    // Esqueleto das fotos de produto que ainda não chegaram (as de fora da tela carregam sob demanda)
    document.querySelectorAll('.prod-image-box img, .product-image-container img').forEach(function (foto) {
        if (foto.complete) return;
        var caixa = foto.parentElement;
        var pronto = function () { caixa.classList.remove('carregando'); };
        caixa.classList.add('carregando');
        foto.addEventListener('load', pronto);
        foto.addEventListener('error', pronto);
    });

    // Esqueleto dos gráficos até a página terminar de carregar (a biblioteca vem de fora)
    document.querySelectorAll('canvas').forEach(function (grafico) {
        var caixa = grafico.parentElement;
        caixa.classList.add('carregando');
        window.addEventListener('load', function () { caixa.classList.remove('carregando'); });
    });
})();
