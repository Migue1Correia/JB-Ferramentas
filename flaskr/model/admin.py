from .db import db_execute

class AdminModel:

    # ==========================
    # GESTÃO DE PERFIS
    # ==========================
    @staticmethod
    def create_perfil(perfil, descricao):
        arg = "INSERT INTO perfis (perfil, descricao) VALUES (%s, %s);"
        res = db_execute(arg, perfil, descricao)
        return True, "Perfil cadastrado com sucesso!" if res[0] else (False, "Erro ao cadastrar perfil.")

    @staticmethod
    def get_perfis():
        res = db_execute("SELECT id, perfil, descricao, ativo FROM perfis;", fetch_type="all")
        return res[1] if res[0] else []

    # ==========================
    # GESTÃO DE FILIAIS
    # ==========================
    @staticmethod
    def create_filial(codigo, nome, endereco):
        arg = "INSERT INTO filiais (codigo_filial, nome, endereco) VALUES (%s, %s, %s);"
        res = db_execute(arg, codigo, nome, endereco)
        return True, "Filial cadastrada com sucesso!" if res[0] else (False, "Erro ao cadastrar filial.")

    @staticmethod
    def get_filiais():
        res = db_execute("SELECT id, codigo_filial, nome, endereco FROM filiais;", fetch_type="all")
        return res[1] if res[0] else []

    # ==========================
    # GESTÃO DE PEÇAS E ESTOQUE
    # ==========================
    @staticmethod
    def create_peca(codigo_barras, nome, fabricante, custo, preco_venda):
        arg = "INSERT INTO pecas (codigo_barras, nome, fabricante, custo, preco_venda) VALUES (%s, %s, %s, %s, %s);"
        res = db_execute(arg, codigo_barras, nome, fabricante, custo, preco_venda)
        return True, "Peça cadastrada no catálogo!" if res[0] else (False, "Erro ao cadastrar peça.")

    @staticmethod
    def add_estoque_peca(id_peca, id_filial, qtd_atual, qtd_minima):
        arg = "INSERT INTO estoque_pecas (id_peca, id_filial, quantidade_atual, quantidade_minima) VALUES (%s, %s, %s, %s);"
        res = db_execute(arg, id_peca, id_filial, qtd_atual, qtd_minima)
        return True, "Estoque de peça atualizado!" if res[0] else (False, "Erro ao lançar estoque.")

    # ==========================
    # GESTÃO DE UNIDADES FÍSICAS (FERRAMENTAS)
    # ==========================
    @staticmethod
    def create_unidade_ferramenta(numero_serie, id_ferramenta, id_filial):
        # A tabela unidade_ferramentas exige o status padrão 'em_estoque'
        arg = "INSERT INTO unidade_ferramentas (numero_serie, id_ferramenta, id_filial, status) VALUES (%s, %s, %s, 'em_estoque');"
        res = db_execute(arg, numero_serie, id_ferramenta, id_filial)
        return True, "Unidade de ferramenta registrada!" if res[0] else (False, "Erro ao registrar unidade física.")