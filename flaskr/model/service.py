from .db import db_execute, jb_solucoes_db

# Como o cliente escolheu pagar uma manutenção aprovada (coluna servicos.pagamento)
PAGAMENTO_RETIRADA = "Na retirada"
PAGAMENTO_PENDENTE = "Online (pendente)"
PAGAMENTO_PAGO = "Pago online"
PAGAMENTO_PAGO_RETIRADA = "Pago na retirada"
# A coluna servicos.pago_em guarda quando o dinheiro entrou. É por ela que o Caixa e o
# Painel de gráficos sabem o que já foi recebido: venda e aluguel na hora do pedido,
# manutenção quando o cliente paga pelo site ou na retirada.


class ServiceModel:

    @staticmethod
    def get_user_history(user_id):
        """
        Busca todos os serviços vinculados ao cliente para exibir no perfil.
        """
        # Nota: Presumi que você adicionou a coluna status_servico na tabela servicos.
        # Se não adicionou, rode no MySQL: ALTER TABLE servicos ADD status_servico VARCHAR(50) DEFAULT 'Aberto';
        # Os LEFT JOIN buscam o nome da ferramenta do pedido (manutenção não tem ferramenta vinculada).
        arg = """
            SELECT s.id, s.servico_solicitado, s.valor_servico, s.data_abertura,
                   s.titulo_servico, f.marca, f.modelo, s.status_servico, s.pagamento,
                   m.equipamento, m.diagnostico, m.foto_equipamento
            FROM servicos s
            LEFT JOIN manutencoes m ON m.id_servico = s.id
            LEFT JOIN servico_ferramentas sf ON sf.id_servico = s.id
            LEFT JOIN unidade_ferramentas u ON u.id = sf.id_unidade_ferramenta
            LEFT JOIN ferramentas f ON f.id = u.id_ferramenta
            WHERE s.id_pessoa_solicitante = %s
            ORDER BY s.data_abertura DESC, s.id DESC;
        """
        res = db_execute(arg, user_id, fetch_type="all")

        if not res[0] or res[1] is None:
            return []

        historico = []
        for id_servico, tipo, valor, data, titulo, marca, modelo, status, pagamento, equipamento, diagnostico, foto in res[1]:
            if equipamento:
                titulo = f"Manutenção: {equipamento}"
            historico.append({
                "id": id_servico,
                "tipo": tipo,
                "valor": valor,
                "data": data,
                "descricao": f"{marca} {modelo}" if marca else titulo,
                "status": status,
                "diagnostico": diagnostico,
                "foto": foto,
                "pagamento": pagamento,
                "pagamento_pendente": pagamento == PAGAMENTO_PENDENTE,
            })
        return historico

    @staticmethod
    def get_unidade_disponivel(ferramenta_id):
        """Busca uma unidade física disponível no estoque para a ferramenta solicitada."""
        # Ajustado para o ENUM correto do seu banco: 'em_estoque'
        arg = "SELECT id FROM unidade_ferramentas WHERE id_ferramenta=%s AND status='em_estoque' LIMIT 1;"
        res = db_execute(arg, ferramenta_id, fetch_type="one")
        if res[0] and res[1]:
            return res[1][0]
        return None

    @staticmethod
    def _registrar_pedido(tipo, titulo, descricao, valor_total, user_id, tool_id, novo_status, dias=None):
        """
        Reserva uma unidade e grava o pedido (venda ou aluguel) em uma única transação:
        ou grava tudo, ou não grava nada.
        :return: True se gravou, None se não há unidade em estoque, False se deu erro.
        """
        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            # FOR UPDATE trava a unidade: se dois clientes clicarem juntos,
            # o segundo espera e não recebe a mesma unidade.
            c.execute("SELECT id FROM unidade_ferramentas WHERE id_ferramenta=%s AND status='em_estoque' LIMIT 1 FOR UPDATE;", (tool_id,))
            unidade = c.fetchone()
            if not unidade:
                conexao.rollback()
                return None

            c.execute("""
                INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, valor_servico, status_servico, pago_em, id_pessoa_solicitante, id_pessoa_abertura)
                VALUES (%s, %s, %s, %s, 'Concluído', NOW(), %s, %s);
            """, (tipo, titulo, descricao, valor_total, user_id, user_id))
            id_servico = c.lastrowid

            if dias:
                # valor_diario guarda a diária cobrada, mesmo que o preço da ferramenta mude depois
                diaria = round(float(valor_total) / int(dias), 2)
                c.execute("INSERT INTO alugueis (id_servico, data_devolucao, valor_diario) VALUES (%s, DATE_ADD(NOW(), INTERVAL %s DAY), %s);",
                          (id_servico, dias, diaria))

            c.execute("INSERT INTO servico_ferramentas (id_servico, id_unidade_ferramenta) VALUES (%s, %s);", (id_servico, unidade[0]))
            c.execute("UPDATE unidade_ferramentas SET status=%s WHERE id=%s;", (novo_status, unidade[0]))
            conexao.commit()
            return True
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return False
        finally:
            c.close()

    @staticmethod
    def create_rental(user_id, tool_id, dias, valor_total):
        """
        Registra um novo aluguel no banco de dados.
        """
        # 'alugada' é o status de aluguel no ENUM do banco
        resultado = ServiceModel._registrar_pedido(
            'aluguel', 'Aluguel de Ferramenta', 'Aluguel solicitado via site',
            valor_total, user_id, tool_id, 'alugada', dias)
        if resultado is None:
            return False, "Desculpe, não temos unidades disponíveis desta ferramenta para aluguel no momento."
        if not resultado:
            return False, "Erro ao processar o serviço de aluguel."
        return True, "Aluguel realizado com sucesso!"

    @staticmethod
    def create_purchase(user_id, tool_id, valor_total):
        """
        Registra uma nova compra no banco de dados.
        """
        # 'baixada' é a opção de venda no ENUM do banco
        resultado = ServiceModel._registrar_pedido(
            'venda', 'Compra de Ferramenta', 'Compra solicitada via site',
            valor_total, user_id, tool_id, 'baixada')
        if resultado is None:
            return False, "Desculpe, ferramenta esgotada em nosso estoque físico."
        if not resultado:
            return False, "Erro ao processar a compra."
        return True, "Compra realizada com sucesso!"

    @staticmethod
    def create_maintenance(user_id, description, tool_details):
        """
        Função para abrir uma nova solicitação de manutenção.
        Grava nas duas tabelas (servicos e manutencoes) em uma única transação:
        ou grava tudo, ou não grava nada.
        """
        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            c.execute("""
                INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, id_pessoa_solicitante, id_pessoa_abertura)
                VALUES ('manutencao', 'Manutenção de Equipamento', %s, %s, %s);
            """, (description, user_id, user_id))
            # "equipamento" é o que o cliente informou; "diagnostico" fica vazio até o colaborador avaliar.
            # A tabela manutencoes pede garantia NOT NULL, por isso o 0.
            c.execute("INSERT INTO manutencoes (id_servico, equipamento, diagnostico, garantia) VALUES (%s, %s, '', 0);",
                      (c.lastrowid, tool_details))
            conexao.commit()
            return True, "Manutenção solicitada com sucesso!"
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return False, "Erro ao registrar a manutenção."
        finally:
            c.close()

    @staticmethod
    def get_resumo_manutencoes(user_id):
        """
        Conta as manutenções do cliente por status, para os avisos da tela de manutenção.
        :return: Dicionário {status: quantidade}. Ex.: {"Aberto": 1, "Concluído": 2}
        """
        arg = """
            SELECT status_servico, COUNT(*) FROM servicos
            WHERE id_pessoa_solicitante = %s AND servico_solicitado = 'manutencao'
            GROUP BY status_servico;
        """
        res = db_execute(arg, user_id, fetch_type="all")
        if not res[0] or res[1] is None:
            return {}
        return dict(res[1])

    @staticmethod
    def get_orcamento(id_servico, id_cliente):
        """
        Busca uma manutenção do cliente (para a tela de pagamento e para o carrinho).
        :return: Dicionário com id, descricao, valor, status, pagamento, equipamento,
                 diagnostico e foto. None se não for dele.
        """
        arg = """
            SELECT s.id, s.descricao_servico, s.valor_servico, s.status_servico, s.pagamento,
                   m.equipamento, m.diagnostico, m.foto_equipamento
            FROM servicos s
            LEFT JOIN manutencoes m ON m.id_servico = s.id
            WHERE s.id=%s AND s.id_pessoa_solicitante=%s AND s.servico_solicitado='manutencao';
        """
        res = db_execute(arg, id_servico, id_cliente, fetch_type="one")
        if not res[0] or not res[1]:
            return None
        return {"id": res[1][0], "descricao": res[1][1], "valor": res[1][2], "status": res[1][3], "pagamento": res[1][4],
                "equipamento": res[1][5], "diagnostico": res[1][6], "foto": res[1][7]}

    @staticmethod
    def pagar_manutencao(id_servico, id_cliente):
        """
        Marca como paga uma manutenção aprovada que o cliente escolheu pagar pelo site.
        """
        arg = """
            UPDATE servicos SET pagamento=%s, pago_em=NOW()
            WHERE id=%s AND id_pessoa_solicitante=%s AND servico_solicitado='manutencao' AND pagamento=%s;
        """
        res = db_execute(arg, PAGAMENTO_PAGO, id_servico, id_cliente, PAGAMENTO_PENDENTE)
        if not res[0] or not res[1]:
            return False, "Esse serviço não está aguardando pagamento."
        return True, "Pagamento da manutenção registrado."

    @staticmethod
    def responder_orcamento(id_servico, id_cliente, resposta, pagamento=None):
        """
        O cliente aprova ou reprova o orçamento feito pelo colaborador.
        Na aprovação, "pagamento" guarda como ele escolheu pagar.
        """
        if resposta not in ['Aprovado', 'Reprovado']:
            return False, "Resposta inválida."

        # Ajuste no nome da coluna: id_pessoa_solicitante
        arg = """
            UPDATE servicos 
            SET status_servico=%s, pagamento=%s 
            WHERE id=%s AND id_pessoa_solicitante=%s AND status_servico='Aguardando Aprovação';
        """
        res = db_execute(arg, resposta, pagamento, id_servico, id_cliente)

        if not res[0]:
            return False, "Erro ao processar a resposta do orçamento."
        if not res[1]:  # nenhuma linha mudou: o pedido não é deste cliente ou já foi respondido
            return False, "Esse orçamento não está aguardando a sua resposta."

        if pagamento == PAGAMENTO_RETIRADA:
            return True, "Orçamento aprovado! O pagamento será feito na retirada do equipamento."
        if pagamento == PAGAMENTO_PENDENTE:
            return True, "Orçamento aprovado! Finalize o pagamento no carrinho."
        return True, f"Orçamento {resposta.lower()} com sucesso!"