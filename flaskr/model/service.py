from .db import db_execute, jb_solucoes_db

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
                   s.titulo_servico, f.marca, f.modelo
            FROM servicos s
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
        for id_servico, tipo, valor, data, titulo, marca, modelo in res[1]:
            historico.append({
                "id": id_servico,
                "tipo": tipo,
                "valor": valor,
                "data": data,
                "descricao": f"{marca} {modelo}" if marca else titulo,
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
                INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, valor_servico, id_pessoa_solicitante, id_pessoa_abertura)
                VALUES (%s, %s, %s, %s, %s, %s);
            """, (tipo, titulo, descricao, valor_total, user_id, user_id))
            id_servico = c.lastrowid

            if dias:
                c.execute("INSERT INTO alugueis (id_servico, data_devolucao) VALUES (%s, DATE_ADD(NOW(), INTERVAL %s DAY));", (id_servico, dias))

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
        Função para abrir uma nova solicitação de manutenção
        """
        arg_servico = """
            INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, id_pessoa_solicitante, id_pessoa_abertura) 
            VALUES ('manutencao', 'Manutenção de Equipamento', %s, %s, %s);
        """
        res_servico = db_execute(arg_servico, description, user_id, user_id)
        
        if not res_servico[0]:
            print(res_servico[1])
            return False, "Erro ao criar o serviço base."

        id_servico = res_servico[1] 

        # A sua tabela manutencoes pede garantia NOT NULL, adicionei 0 como padrão inicial
        arg_manu = "INSERT INTO manutencoes (id_servico, diagnostico, garantia) VALUES (%s, %s, 0);"
        res_manu = db_execute(arg_manu, id_servico, tool_details)

        if not res_manu[0]:
            return False, "Erro ao registrar detalhes da manutenção."

        return True, "Manutenção solicitada com sucesso!"

    @staticmethod
    def responder_orcamento(id_servico, id_cliente, resposta):
        """
        O cliente aprova ou reprova o orçamento feito pelo colaborador.
        """
        if resposta not in ['Aprovado', 'Reprovado']:
            return False, "Resposta inválida."

        # Ajuste no nome da coluna: id_pessoa_solicitante
        arg = """
            UPDATE servicos 
            SET status_servico=%s 
            WHERE id=%s AND id_pessoa_solicitante=%s AND status_servico='Aguardando Aprovação';
        """
        res = db_execute(arg, resposta, id_servico, id_cliente)

        if not res[0]:
            return False, "Erro ao processar a resposta do orçamento."

        return True, f"Orçamento {resposta.lower()} com sucesso!"