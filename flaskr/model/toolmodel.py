from .db import db_execute

# Colunas na mesma ordem em que o montar_item lê a linha
COLUNAS = "id, marca, modelo, descricao, preco, tipo_oferta, imagem"

# Foto usada quando a ferramenta não tem imagem cadastrada
IMAGEM_PADRAO = "img/produto.png"

TIPOS_OFERTA = ("Comprar", "Alugar")


class ToolModel:

    @staticmethod
    def montar_item(linha):
        """
        Transforma uma linha da tabela ferramentas no formato que as telas usam.
        No aluguel, "preco" é o valor da diária.
        """
        tool_id, marca, modelo, descricao, preco, tipo, imagem = linha
        return {
            "id": tool_id,
            "marca": marca,
            "modelo": modelo,
            "nome": f"{marca} {modelo}",
            "descricao": descricao,
            "preco": float(preco),
            "tipo": tipo,
            "imagem": imagem or IMAGEM_PADRAO,
        }

    @staticmethod
    def get_all(limit=None):
        arg = f"SELECT {COLUNAS} FROM ferramentas ORDER BY id"
        if limit:
            arg += f" LIMIT {int(limit)}"

        res = db_execute(arg, fetch_type="all")
        if not res[0]:
            print(res[1])
            return []
        return [ToolModel.montar_item(linha) for linha in res[1]]

    @staticmethod
    def get_by_id(tool_id):
        if not tool_id:
            return None

        arg = f"SELECT {COLUNAS} FROM ferramentas WHERE id=%s"
        res = db_execute(arg, tool_id, fetch_type="one")

        if not res[0] or res[1] is None:
            print(res[1])
            return None

        return ToolModel.montar_item(res[1])

    @staticmethod
    def create(marca, modelo, descricao, id_tipo, preco, tipo_oferta, imagem=None):
        if not marca or not modelo or not id_tipo:
            return False, "Preencha os campos obrigatórios (Marca, Modelo e Tipo)."

        try:
            preco = float(preco)
        except (TypeError, ValueError):
            preco = -1
        if preco < 0:
            return False, "Informe um preço válido."

        if tipo_oferta not in TIPOS_OFERTA:
            return False, "Escolha se a ferramenta é para comprar ou alugar."

        arg = """
            INSERT INTO ferramentas (marca, modelo, descricao, id_ferramenta_tipo, preco, tipo_oferta, imagem)
            VALUES (%s, %s, %s, %s, %s, %s, %s);
        """
        res = db_execute(arg, marca, modelo, descricao, id_tipo, preco, tipo_oferta, imagem)

        if not res[0]:
            print(res[1])
            return False, "Erro ao cadastrar a ferramenta no banco de dados."

        return True, "Ferramenta cadastrada com sucesso!"

    @staticmethod
    def get_tipos():
        arg = "SELECT id, tipo FROM ferramenta_tipos;"
        res = db_execute(arg, fetch_type="all")
        if not res[0] or res[1] is None:
            return []
        return res[1]
