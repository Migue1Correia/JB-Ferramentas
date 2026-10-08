from datetime import date

from .db import db_execute

# Tipos de serviço (coluna servico_solicitado da tabela servicos) e o nome exibido no painel
TIPOS_SERVICO = [
    ("venda", "Vendas"),
    ("aluguel", "Aluguéis"),
    ("manutencao", "Manutenções"),
]

NOMES_MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
               "jul", "ago", "set", "out", "nov", "dez"]


class PainelModel:

    @staticmethod
    def get_resumo_mensal(meses=12):
        """
        Monta os dados do painel de gráficos: faturamento e quantidade de serviços
        por mês, separados por tipo (venda, aluguel e manutenção).
        :param meses: Quantos meses mostrar, contando o mês atual.
        :return: Dicionário pronto para o template (rótulos dos meses, séries e totais).
        """
        # 1. Lista dos meses do período, do mais antigo para o mais recente: [(ano, mes), ...]
        hoje = date.today()
        periodo = []
        for i in range(meses - 1, -1, -1):
            ano, mes = divmod(hoje.year * 12 + hoje.month - 1 - i, 12)
            periodo.append((ano, mes + 1))

        data_inicial = date(periodo[0][0], periodo[0][1], 1)

        # 2. Uma única consulta: soma dos valores e contagem dos serviços por mês e por tipo
        arg = """
            SELECT YEAR(data_abertura), MONTH(data_abertura), servico_solicitado,
                   SUM(valor_servico), COUNT(*)
            FROM servicos
            WHERE data_abertura >= %s
            GROUP BY YEAR(data_abertura), MONTH(data_abertura), servico_solicitado;
        """
        res = db_execute(arg, data_inicial, fetch_type="all")

        erro = not res[0]
        linhas = res[1] if res[0] and res[1] else []

        # 3. Guarda o resultado em um dicionário para achar rápido: (ano, mes, tipo) -> (valor, quantidade)
        encontrados = {}
        for ano, mes, tipo, valor, quantidade in linhas:
            encontrados[(ano, mes, tipo)] = (float(valor or 0), int(quantidade))

        # 4. Monta uma série por tipo, preenchendo com zero os meses sem movimento
        series = []
        for chave, nome in TIPOS_SERVICO:
            valores = []
            quantidades = []
            for ano, mes in periodo:
                valor, quantidade = encontrados.get((ano, mes, chave), (0.0, 0))
                valores.append(valor)
                quantidades.append(quantidade)
            series.append({
                "chave": chave,
                "nome": nome,
                "valores": valores,
                "quantidades": quantidades,
                "total_valor": sum(valores),
                "total_quantidade": sum(quantidades),
            })

        return {
            "erro": erro,
            "meses": meses,
            "rotulos": [f"{NOMES_MESES[mes - 1]}/{str(ano)[2:]}" for ano, mes in periodo],
            "series": series,
            "faturamento_total": sum(s["total_valor"] for s in series),
            "total_servicos": sum(s["total_quantidade"] for s in series),
        }
