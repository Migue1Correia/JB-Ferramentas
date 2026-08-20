from .db import db_execute


class ToolModel:

    @staticmethod
    def get_all(limit=None):
        arg = "SELECT * FROM ferramentas"
        if limit:
            arg += f" LIMIT {limit}"

        res = db_execute(arg, fetch_type="all")
        if not res[0]:
            print(res[1])
            return None
        return res[1]

    @staticmethod
    def get_by_id(tool_id):
        if not tool_id:
            return None

        arg = "SELECT * FROM ferramentas WHERE id=%s"
        res = db_execute(arg, tool_id, fetch_type="one")

        if not res[0] or res[1] is None:
            print(res[1])
            return None

        return {
            "id": res[1][0],
            "marca": res[1][1],
            "modelo": res[1][2],
            "descricao": res[1][3],
            "fk_ferramenta_tipo_id": res[1][4],
            "criando_em": res[1][5],
            "atualizado_em": res[1][6]
        }

    @staticmethod
    def create(marca, modelo, descricao, id_tipo):
        if not marca or not modelo or not id_tipo:
            return False, "Preencha os campos obrigatórios (Marca, Modelo e Tipo)."

        arg = """
            INSERT INTO ferramentas (marca, modelo, descricao, id_ferramenta_tipo) 
            VALUES (%s, %s, %s, %s);
        """
        res = db_execute(arg, marca, modelo, descricao, id_tipo)

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
