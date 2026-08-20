from .db import db_execute

class ServiceModel:

    @staticmethod
    def get_user_history(user_id):
        """
        Busca todos os serviços vinculados ao cliente para exibir no perfil.
        """
        # Nota: Presumi que você adicionou a coluna status_servico na tabela servicos.
        # Se não adicionou, rode no MySQL: ALTER TABLE servicos ADD status_servico VARCHAR(50) DEFAULT 'Aberto';
        arg = "SELECT id, servico_solicitado, valor_servico, data_abertura FROM servicos WHERE id_pessoa_solicitante = %s ORDER BY data_abertura DESC;"
        res = db_execute(arg, user_id, fetch_type="all")

        if not res[0] or res[1] is None:
            return []

        return res[1]

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
    def create_rental(user_id, tool_id, dias, valor_total):
        """
        Registra um novo aluguel no banco de dados.
        """
        # 1. Verifica se tem unidade física disponível
        id_unidade = ServiceModel.get_unidade_disponivel(tool_id)
        if not id_unidade:
            return False, "Desculpe, não temos unidades disponíveis desta ferramenta para aluguel no momento."

        # 2. Cria o serviço base respeitando as colunas NOT NULL do seu banco
        arg_servico = """
            INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, valor_servico, id_pessoa_solicitante, id_pessoa_abertura) 
            VALUES ('aluguel', 'Aluguel de Ferramenta', 'Aluguel solicitado via site', %s, %s, %s);
        """
        res_servico = db_execute(arg_servico, valor_total, user_id, user_id)

        if not res_servico[0]:
            print(res_servico[1]) # Para depuração no terminal
            return False, "Erro ao processar o serviço de aluguel."

        id_servico = res_servico[1]

        # 3. Registra na tabela filha de alugueis
        arg_aluguel = "INSERT INTO alugueis (id_servico, data_devolucao) VALUES (%s, DATE_ADD(NOW(), INTERVAL %s DAY));"
        db_execute(arg_aluguel, id_servico, dias)

        # 4. Módulo 2: Vincula a unidade e muda o status para 'alugada' (ENUM do banco)
        arg_vinculo = "INSERT INTO servico_ferramentas (id_servico, id_unidade_ferramenta) VALUES (%s, %s);"
        db_execute(arg_vinculo, id_servico, id_unidade)

        arg_status = "UPDATE unidade_ferramentas SET status='alugada' WHERE id=%s;"
        db_execute(arg_status, id_unidade)

        return True, "Aluguel realizado com sucesso!"

    @staticmethod
    def create_purchase(user_id, tool_id, valor_total):
        """
        Registra uma nova compra no banco de dados.
        """
        # 1. Verifica se tem unidade física disponível
        id_unidade = ServiceModel.get_unidade_disponivel(tool_id)
        if not id_unidade:
            return False, "Desculpe, ferramenta esgotada em nosso estoque físico."

        # 2. Cria o serviço base respeitando as colunas
        arg_servico = """
            INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, valor_servico, id_pessoa_solicitante, id_pessoa_abertura) 
            VALUES ('venda', 'Compra de Ferramenta', 'Compra solicitada via site', %s, %s, %s);
        """
        res_servico = db_execute(arg_servico, valor_total, user_id, user_id)

        if not res_servico[0]:
            print(res_servico[1])
            return False, "Erro ao processar a compra."

        id_servico = res_servico[1]

        # 3. Módulo 2: Vincula a unidade e dá baixa ('baixada' é a opção de venda no seu ENUM)
        arg_compra = "INSERT INTO servico_ferramentas (id_servico, id_unidade_ferramenta) VALUES (%s, %s);"
        db_execute(arg_compra, id_servico, id_unidade)

        arg_status = "UPDATE unidade_ferramentas SET status='baixada' WHERE id=%s;"
        db_execute(arg_status, id_unidade)

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