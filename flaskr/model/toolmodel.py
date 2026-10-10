from .db import db_execute

# Colunas na mesma ordem em que o montar_item lê a linha
COLUNAS = "id, marca, modelo, descricao, preco, tipo_oferta, imagem, ativo"

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
        tool_id, marca, modelo, descricao, preco, tipo, imagem, ativo = linha
        return {
            "id": tool_id,
            "marca": marca,
            "modelo": modelo,
            "nome": f"{marca} {modelo}",
            "descricao": descricao,
            "preco": float(preco),
            "tipo": tipo,
            "imagem": imagem or IMAGEM_PADRAO,
            "ativo": bool(ativo),
        }

    @staticmethod
    def get_all(limit=None, apenas_ativas=True):
        """
        Lista as ferramentas. A loja usa só as ativas; o Catálogo do colaborador
        pede todas (apenas_ativas=False), para poder reativar.
        """
        arg = f"SELECT {COLUNAS} FROM ferramentas"
        if apenas_ativas:
            arg += " WHERE ativo=1"
        arg += " ORDER BY id"
        if limit:
            arg += f" LIMIT {int(limit)}"

        res = db_execute(arg, fetch_type="all")
        if not res[0]:
            print(res[1])
            return []
        return [ToolModel.montar_item(linha) for linha in res[1]]

    @staticmethod
    def get_by_id(tool_id, apenas_ativa=True):
        """
        Busca uma ferramenta. Por padrão ignora as desativadas, para a loja, os detalhes
        e o carrinho não venderem o que saiu de linha.
        """
        if not tool_id:
            return None

        arg = f"SELECT {COLUNAS} FROM ferramentas WHERE id=%s"
        if apenas_ativa:
            arg += " AND ativo=1"
        res = db_execute(arg, tool_id, fetch_type="one")

        if not res[0] or res[1] is None:
            print(res[1])
            return None

        return ToolModel.montar_item(res[1])

    @staticmethod
    def _validar(marca, modelo, preco, tipo_oferta):
        """Confere os campos da ferramenta. Devolve (preço como número, mensagem de erro ou None)."""
        if not (marca or "").strip() or not (modelo or "").strip():
            return None, "Preencha os campos obrigatórios (Marca e Modelo)."

        try:
            preco = float(preco)
        except (TypeError, ValueError):
            preco = -1
        if preco < 0:
            return None, "Informe um preço válido."

        if tipo_oferta not in TIPOS_OFERTA:
            return None, "Escolha se a ferramenta é para comprar ou alugar."
        return preco, None

    @staticmethod
    def create(marca, modelo, descricao, id_tipo, preco, tipo_oferta, imagem=None):
        if not id_tipo:
            return False, "Preencha os campos obrigatórios (Marca, Modelo e Tipo)."
        preco, erro = ToolModel._validar(marca, modelo, preco, tipo_oferta)
        if erro:
            return False, erro

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
    def update(tool_id, marca, modelo, descricao, preco, tipo_oferta, imagem=None):
        """Altera os dados de uma ferramenta. Sem foto nova, a foto atual é mantida."""
        preco, erro = ToolModel._validar(marca, modelo, preco, tipo_oferta)
        if erro:
            return False, erro

        arg = """
            UPDATE ferramentas
            SET marca=%s, modelo=%s, descricao=%s, preco=%s, tipo_oferta=%s, imagem=COALESCE(%s, imagem)
            WHERE id=%s;
        """
        res = db_execute(arg, marca, modelo, descricao, preco, tipo_oferta, imagem, tool_id)
        if not res[0]:
            print(res[1])
            return False, "Erro ao alterar a ferramenta no banco de dados."
        return True, "Ferramenta alterada com sucesso!"

    @staticmethod
    def definir_ativo(tool_id, ativo):
        """Desativa (some da loja, mas o histórico de pedidos fica) ou reativa uma ferramenta."""
        res = db_execute("UPDATE ferramentas SET ativo=%s WHERE id=%s;", 1 if ativo else 0, tool_id)
        if not res[0]:
            print(res[1])
            return False
        return True

    @staticmethod
    def get_tipos():
        arg = "SELECT id, tipo FROM ferramenta_tipos;"
        res = db_execute(arg, fetch_type="all")
        if not res[0] or res[1] is None:
            return []
        return res[1]
