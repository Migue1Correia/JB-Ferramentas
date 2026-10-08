from .db import db_execute


# Preço, tipo de oferta e foto dos produtos de exemplo (cadastrados pelo cadastrar_exemplos.py).
# A tabela "ferramentas" ainda não tem colunas para isso, então por enquanto esses dados
# ficam aqui, ligados pelo modelo da ferramenta. Quando o banco ganhar essas colunas,
# este dicionário pode ser apagado.
CATALOGO_EXEMPLOS = {
    "Parafusadeira e Furadeira a Bateria 20V": {"preco": 459.90, "tipo": "Comprar", "imagem": "img/produto2.png"},
    "Parafusadeira e Furadeira 12V": {"preco": 329.90, "tipo": "Comprar", "imagem": "img/produto3.png"},
    "Furadeira de Impacto 750W": {"preco": 35.00, "tipo": "Alugar", "imagem": "img/produto.png"},
}

# Usado para as ferramentas que não estão no catálogo de exemplos
OFERTA_PADRAO = {"preco": 150.00, "tipo": "Comprar/Alugar", "imagem": "img/produto.png"}


class ToolModel:

    @staticmethod
    def montar_item(tool_id, marca, modelo, descricao=None):
        """
        Junta os dados da ferramenta (vindos do banco) com preço, tipo de oferta e foto,
        no formato que as telas da loja usam.
        """
        oferta = CATALOGO_EXEMPLOS.get(modelo, OFERTA_PADRAO)
        return {
            "id": tool_id,
            "nome": f"{marca} {modelo}",
            "descricao": descricao,
            "preco": oferta["preco"],
            "tipo": oferta["tipo"],
            "imagem": oferta["imagem"],
        }

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
