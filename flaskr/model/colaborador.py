from .db import db_execute
from .service import PAGAMENTO_PAGO, PAGAMENTO_PAGO_RETIRADA

# Status que o colaborador pode dar a um orçamento
STATUS_ORCAMENTO = ('Aguardando Aprovação', 'Concluído')


class ColaboradorModel:

    @staticmethod
    def get_servicos_pendentes():
        """
        Busca os serviços abertos, que ainda precisam do orçamento do colaborador.
        Faz um JOIN com a tabela de pessoas para pegar o nome do cliente.
        """
        arg = """
            SELECT s.id, p.nome, s.descricao_servico, s.status_servico, s.data_abertura 
            FROM servicos s
            JOIN pessoas p ON s.id_pessoa_solicitante = p.id
            WHERE s.servico_solicitado = 'manutencao' AND s.status_servico = 'Aberto'
            ORDER BY s.data_abertura ASC;
        """
        res = db_execute(arg, fetch_type="all")

        if not res[0] or res[1] is None:
            return []

        # Opcional: Formatar a saída como um dicionário para facilitar no frontend
        servicos = []
        for row in res[1]:
            servicos.append({
                "id": row[0],
                "cliente": row[1],
                "descricao": row[2],
                "status": row[3],
                "data": row[4]
            })
        return servicos

    @staticmethod
    def atualizar_orcamento(id_servico, valor, status, caminho_imagem=None, detalhes_dano=""):
        """
        O colaborador insere o valor do serviço e muda o status (ex: 'Aguardando Aprovação' ou 'Concluído').
        Também salva o diagnóstico e a foto do equipamento danificado.
        """
        if status not in STATUS_ORCAMENTO:
            return False, "Status inválido."

        try:
            valor = float(valor)
        except (TypeError, ValueError):
            valor = -1
        if valor < 0:
            return False, "Informe um valor válido (zero ou mais)."

        # Só manutenção ainda pendente recebe orçamento (nunca uma venda ou um serviço já fechado).
        # "Reprovado" entra na lista para o colaborador poder mandar um orçamento novo.
        atual = db_execute("SELECT servico_solicitado, status_servico FROM servicos WHERE id=%s;", id_servico, fetch_type="one")
        if not atual[0] or not atual[1] or atual[1][0] != 'manutencao' or atual[1][1] not in ('Aberto', 'Aguardando Aprovação', 'Reprovado'):
            return False, "Só dá para fazer orçamento de manutenções pendentes."

        arg = "UPDATE servicos SET valor_servico=%s, status_servico=%s WHERE id=%s;"
        res = db_execute(arg, valor, status, id_servico)

        if not res[0]:
            return False, "Erro ao atualizar o orçamento."

        # Guarda o diagnóstico e a foto na tabela 'manutencoes'.
        # COALESCE mantém a foto que já existia quando nenhuma nova é enviada.
        if caminho_imagem or detalhes_dano:
            arg_manu = "UPDATE manutencoes SET diagnostico=%s, foto_equipamento=COALESCE(%s, foto_equipamento) WHERE id_servico=%s;"
            db_execute(arg_manu, detalhes_dano, caminho_imagem, id_servico)

        return True, "Orçamento, avaliação e foto registrados com sucesso!"

    # === ORÇAMENTOS QUE O CLIENTE JÁ RESPONDEU ===
    @staticmethod
    def get_orcamentos_respondidos():
        """
        Lista as manutenções com orçamento enviado: aguardando a resposta do cliente
        ou aprovado (falta fazer o serviço).
        """
        return ColaboradorModel._manutencoes_com_status("('Aguardando Aprovação', 'Aprovado')")

    @staticmethod
    def get_orcamentos_reprovados():
        """Lista as manutenções que o cliente reprovou: falta mandar outro orçamento ou devolver o equipamento."""
        return ColaboradorModel._manutencoes_com_status("('Reprovado')")

    @staticmethod
    def get_prontos_para_retirada():
        """Lista as manutenções concluídas que o cliente ainda não veio buscar."""
        return ColaboradorModel._manutencoes_com_status("('Concluído')")

    @staticmethod
    def entregar_servico(id_servico):
        """
        Registra que o cliente retirou o equipamento. Quem não tinha pago pelo site
        paga na retirada, e é aí que o valor entra no caixa.
        """
        arg = """
            UPDATE servicos
            SET status_servico = 'Entregue',
                pago_em = IF(pagamento = %s, pago_em, NOW()),
                pagamento = IF(pagamento = %s, pagamento, %s)
            WHERE id = %s AND servico_solicitado = 'manutencao' AND status_servico = 'Concluído';
        """
        res = db_execute(arg, PAGAMENTO_PAGO, PAGAMENTO_PAGO, PAGAMENTO_PAGO_RETIRADA, id_servico)
        if not res[0] or not res[1]:
            return False, "Esse serviço não está pronto para retirada."
        return True, "Entrega registrada."

    @staticmethod
    def _manutencoes_com_status(status_sql):
        arg = f"""
            SELECT s.id, p.nome, p.telefone, s.descricao_servico, s.status_servico, s.valor_servico, s.pagamento
            FROM servicos s
            JOIN pessoas p ON s.id_pessoa_solicitante = p.id
            WHERE s.servico_solicitado = 'manutencao' AND s.status_servico IN {status_sql}
            ORDER BY s.data_abertura ASC;
        """
        res = db_execute(arg, fetch_type="all")
        if not res[0] or res[1] is None:
            return []
        return [{"id": linha[0], "cliente": linha[1], "telefone": linha[2], "descricao": linha[3],
                 "status": linha[4], "valor": linha[5], "pagamento": linha[6],
                 "pago": linha[6] == PAGAMENTO_PAGO} for linha in res[1]]

    @staticmethod
    def fechar_servico(id_servico):
        """
        Fecha uma manutenção já respondida pelo cliente:
        aprovada vira 'Concluído' (pronta para retirada), reprovada vira 'Encerrado'.
        """
        arg = """
            UPDATE servicos
            SET status_servico = IF(status_servico = 'Aprovado', 'Concluído', 'Encerrado')
            WHERE id = %s AND servico_solicitado = 'manutencao' AND status_servico IN ('Aprovado', 'Reprovado');
        """
        res = db_execute(arg, id_servico)
        if not res[0] or not res[1]:
            return False, "Esse serviço não está aguardando fechamento."
        return True, "Serviço fechado."

    # === DEVOLUÇÃO DE ALUGUEL ===
    @staticmethod
    def get_alugueis_em_aberto():
        """
        Lista os aluguéis cuja ferramenta ainda não foi devolvida, do prazo mais antigo para o mais novo.
        """
        arg = """
            SELECT a.id_servico, p.nome, f.marca, f.modelo, a.data_devolucao, a.data_devolucao < NOW()
            FROM alugueis a
            JOIN servicos s ON s.id = a.id_servico
            JOIN pessoas p ON p.id = s.id_pessoa_solicitante
            JOIN servico_ferramentas sf ON sf.id_servico = a.id_servico
            JOIN unidade_ferramentas u ON u.id = sf.id_unidade_ferramenta
            JOIN ferramentas f ON f.id = u.id_ferramenta
            WHERE a.devolvido_em IS NULL
            ORDER BY a.data_devolucao;
        """
        res = db_execute(arg, fetch_type="all")
        if not res[0] or res[1] is None:
            return []
        return [{"id": linha[0], "cliente": linha[1], "ferramenta": f"{linha[2]} {linha[3]}",
                 "prazo": linha[4], "atrasado": bool(linha[5])} for linha in res[1]]

    @staticmethod
    def registrar_devolucao(id_servico):
        """
        Marca o aluguel como devolvido e devolve a unidade ao estoque, em um comando só.
        """
        arg = """
            UPDATE alugueis a
            JOIN servico_ferramentas sf ON sf.id_servico = a.id_servico
            JOIN unidade_ferramentas u ON u.id = sf.id_unidade_ferramenta
            SET a.devolvido_em = NOW(), u.status = 'em_estoque'
            WHERE a.id_servico = %s AND a.devolvido_em IS NULL;
        """
        res = db_execute(arg, id_servico)
        if not res[0] or not res[1]:
            return False, "Aluguel não encontrado ou já devolvido."
        return True, "Devolução registrada. A ferramenta voltou para o estoque."

    # === MÓDULO 3: REGISTRO DE CAIXA / FINANCEIRO ===
    @staticmethod
    def get_relatorio_caixa():
        """
        Soma o que já foi recebido (pago_em preenchido): vendas e aluguéis e manutenções pagas.
        """
        arg = "SELECT SUM(valor_servico) FROM servicos WHERE pago_em IS NOT NULL;"
        res = db_execute(arg, fetch_type="one")

        lucro_total = 0
        if res[0] and res[1] and res[1][0] is not None:
            lucro_total = res[1][0]

        # Busca detalhes para montar a tabela do caixa
        arg_lista = "SELECT id, descricao_servico, status_servico, valor_servico, pago_em FROM servicos WHERE pago_em IS NOT NULL ORDER BY pago_em DESC;"
        res_lista = db_execute(arg_lista, fetch_type="all")

        servicos_caixa = []
        if res_lista[0] and res_lista[1]:
            for row in res_lista[1]:
                servicos_caixa.append({
                    "id": row[0],
                    "descricao": row[1],
                    "status": row[2],
                    "valor": row[3],
                    "data": row[4]
                })

        return {"lucro_total": lucro_total, "historico": servicos_caixa}
