// Painel com gráficos (painel_graficos.html)
// Desenha os gráficos com a biblioteca Chart.js, usando os dados que o Flask
// deixou na página dentro da tag <script id="dados-painel">.

(function () {
    const dados = JSON.parse(document.getElementById('dados-painel').textContent);

    // Uma cor fixa para cada tipo de serviço (as mesmas do styleJB.css)
    const CORES = {
        venda: '#3987e5',
        aluguel: '#d95926',
        manutencao: '#199e70'
    };
    const COR_FUNDO = '#141414';
    const COR_TEXTO = '#c3c2b7';
    const COR_GRADE = '#2c2c2a';

    const formatoMoeda = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

    Chart.defaults.color = COR_TEXTO;
    Chart.defaults.font.family = "'Segoe UI', Tahoma, Geneva, Verdana, sans-serif";

    // Cria um gráfico de barras empilhadas: uma barra por mês, dividida por tipo de serviço
    function criarGrafico(idCanvas, campo, formatar) {
        const series = dados.series.map(function (serie) {
            return {
                label: serie.nome,
                data: serie[campo],
                backgroundColor: CORES[serie.chave],
                borderColor: COR_FUNDO,
                borderWidth: 1,
                borderRadius: 3,
                maxBarThickness: 28
            };
        });

        new Chart(document.getElementById(idCanvas), {
            type: 'bar',
            data: { labels: dados.rotulos, datasets: series },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { mode: 'index', intersect: false },
                scales: {
                    x: { stacked: true, grid: { display: false } },
                    y: {
                        stacked: true,
                        beginAtZero: true,
                        grid: { color: COR_GRADE },
                        ticks: {
                            precision: 0,
                            callback: function (valor) { return formatar(valor); }
                        }
                    }
                },
                plugins: {
                    legend: { position: 'bottom', labels: { boxWidth: 12, boxHeight: 12 } },
                    tooltip: {
                        callbacks: {
                            label: function (item) {
                                return item.dataset.label + ': ' + formatar(item.parsed.y);
                            },
                            footer: function (itens) {
                                const total = itens.reduce(function (soma, item) { return soma + item.parsed.y; }, 0);
                                return 'Total: ' + formatar(total);
                            }
                        }
                    }
                }
            }
        });
    }

    criarGrafico('grafico-faturamento', 'valores', function (valor) { return formatoMoeda.format(valor); });
    criarGrafico('grafico-quantidade', 'quantidades', function (valor) { return String(valor); });
})();
