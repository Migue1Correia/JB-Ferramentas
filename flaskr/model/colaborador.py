from .db import db_execute


class ColaboradorModel:

    @staticmethod
    def get_servicos_pendentes():
        """
        Busca todos os serviços que precisam de atenção do colaborador.
        Faz um JOIN com a tabela de pessoas para pegar o nome do cliente.
        """
        arg = """
            SELECT s.id, p.nome, s.descricao_servico, s.status_servico, s.data_abertura 
            FROM servicos s
            JOIN pessoas p ON s.fk_pessoa_solicitante_id = p.id
            WHERE s.status_servico = 'Aberto' OR s.status_servico = 'Aguardando Aprovação'
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
    def atualizar_orcamento(id_servico, id_colaborador, valor, status, caminho_imagem=None, detalhes_dano=""):
        """
        O colaborador insere o valor do serviço e muda o status (ex: 'Aguardando Aprovação' ou 'Concluído').
        Também salva a foto do equipamento danificado e cria um registro no histórico.
        """
        # Sua lógica original mantida
        arg = "UPDATE servicos SET valor_servico=%s, status_servico=%s WHERE id=%s;"
        res = db_execute(arg, valor, status, id_servico)

        if not res[0]:
            return False, "Erro ao atualizar o orçamento."

        # AJUSTE: Atualiza a tabela 'manutencoes' com a foto e o diagnóstico do problema
        if caminho_imagem or detalhes_dano:
            # Dica: Certifique-se de que a tabela 'manutencoes' possui uma coluna como 'foto_equipamento'
            arg_manu = "UPDATE manutencoes SET diagnostico=%s, foto_equipamento=%s WHERE id_servico=%s;"
            db_execute(arg_manu, detalhes_dano, caminho_imagem, id_servico)

        # AJUSTE: Registra a ação no histórico para o cliente poder ver quem avaliou e o que foi feito
        titulo_historico = "Avaliação e Orçamento Gerado"
        descricao_historico = f"Status atualizado para: {status}. Valor orçado: R$ {valor}."
        arg_hist = """
            INSERT INTO servico_historicos (id_servico, fk_pessoa_responsavel_id, titulo, descricao_atividade) 
            VALUES (%s, %s, %s, %s);
        """
        db_execute(arg_hist, id_servico, id_colaborador,
                   titulo_historico, descricao_historico)

        return True, "Orçamento, avaliação e foto registrados com sucesso!"

        # === MÓDULO 1: GESTÃO DE PEÇAS NA MANUTENÇÃO ===
    @staticmethod
    def adicionar_peca_manutencao(id_servico, id_estoque_peca, quantidade):
        """
        Adiciona uma peça ao orçamento da manutenção e dá baixa no estoque.
        """
        # 1. Pega o ID da manutenção vinculada ao serviço
        arg_get_manu = "SELECT id FROM manutencoes WHERE id_servico=%s;"
        res_manu = db_execute(arg_get_manu, id_servico, fetch_type="one")

        if not res_manu[0] or not res_manu[1]:
            return False, "Registro de manutenção não encontrado."

        id_manutencao = res_manu[1][0]

        # 2. Insere na tabela manutencao_pecas
        arg_insert = "INSERT INTO manutencao_pecas (id_manutencao, id_estoque_peca, quantidade) VALUES (%s, %s, %s);"
        res_insert = db_execute(arg_insert, id_manutencao,
                                id_estoque_peca, quantidade)

        if not res_insert[0]:
            return False, "Erro ao adicionar peça ao serviço."

        # 3. Dá baixa na quantidade_atual da tabela estoque_pecas
        arg_baixa = "UPDATE estoque_pecas SET quantidade_atual = quantidade_atual - %s WHERE id = %s;"
        db_execute(arg_baixa, quantidade, id_estoque_peca)

        return True, "Peça adicionada e estoque atualizado com sucesso!"

    # === MÓDULO 3: REGISTRO DE CAIXA / FINANCEIRO ===
    @staticmethod
    def get_relatorio_caixa():
        """
        Calcula o lucro obtido somando serviços aprovados/concluídos.
        """
        arg = "SELECT SUM(valor_servico) FROM servicos WHERE status_servico IN ('Aprovado', 'Concluído');"
        res = db_execute(arg, fetch_type="one")

        lucro_total = 0
        if res[0] and res[1] and res[1][0] is not None:
            lucro_total = res[1][0]

        # Busca detalhes para montar a tabela do caixa
        arg_lista = "SELECT id, descricao_servico, status_servico, valor_servico, data_abertura FROM servicos WHERE status_servico IN ('Aprovado', 'Concluído') ORDER BY data_abertura DESC;"
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
