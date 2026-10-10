from .db import db_execute, jb_solucoes_db


class PecaModel:

    @staticmethod
    def listar():
        """
        Lista as peças com o estoque de cada filial, em ordem de nome.
        "falta" avisa quando a quantidade está igual ou abaixo do mínimo.
        """
        arg = """
            SELECT p.id, p.codigo_barras, p.nome, p.fabricante, p.custo, p.preco_venda,
                   f.nome, e.quantidade_atual, e.quantidade_minima, e.id
            FROM pecas p
            JOIN estoque_pecas e ON e.id_peca = p.id
            JOIN filiais f ON f.id = e.id_filial
            ORDER BY p.nome, f.nome;
        """
        res = db_execute(arg, fetch_type="all")
        if not res[0] or res[1] is None:
            return []
        return [{"id": l[0], "codigo": l[1], "nome": l[2], "fabricante": l[3], "custo": l[4], "preco": l[5],
                 "filial": l[6], "quantidade": l[7], "minimo": l[8], "id_estoque": l[9],
                 "falta": l[7] <= l[8]} for l in res[1]]

    @staticmethod
    def criar(codigo_barras, nome, fabricante, custo, preco_venda, id_filial, quantidade, minimo):
        """
        Cadastra uma peça e o estoque dela na filial, em uma única transação.
        """
        if not codigo_barras or not nome or not fabricante or not id_filial:
            return False, "Preencha código de barras, nome, fabricante e filial."
        if len(codigo_barras) > 20 or len(nome) > 100 or len(fabricante) > 100:
            return False, "Código de barras com até 20 caracteres; nome e fabricante com até 100."
        try:
            custo, preco_venda = float(custo), float(preco_venda)
            quantidade, minimo = int(quantidade), int(minimo)
        except (TypeError, ValueError):
            return False, "Informe números válidos para custo, preço e quantidades."
        if min(custo, preco_venda, quantidade, minimo) < 0:
            return False, "Custo, preço e quantidades não podem ser negativos."

        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            c.execute("INSERT INTO pecas (codigo_barras, nome, fabricante, custo, preco_venda) VALUES (%s, %s, %s, %s, %s);",
                      (codigo_barras, nome, fabricante, custo, preco_venda))
            c.execute("INSERT INTO estoque_pecas (id_peca, id_filial, quantidade_atual, quantidade_minima) VALUES (%s, %s, %s, %s);",
                      (c.lastrowid, id_filial, quantidade, minimo))
            conexao.commit()
            return True, "Peça cadastrada com sucesso!"
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            if "Duplicate" in str(e):
                return False, "Esse código de barras já existe em outra peça."
            return False, "Erro ao cadastrar a peça. Confira a filial escolhida."
        finally:
            c.close()

    @staticmethod
    def ajustar_estoque(id_estoque, quantidade):
        """Define a quantidade em estoque de uma peça em uma filial (contagem ou entrada de mercadoria)."""
        try:
            quantidade = int(quantidade)
        except (TypeError, ValueError):
            quantidade = -1
        if quantidade < 0:
            return False, "Informe uma quantidade válida."

        res = db_execute("UPDATE estoque_pecas SET quantidade_atual=%s WHERE id=%s;", quantidade, id_estoque)
        if not res[0]:
            return False, "Erro ao atualizar o estoque."
        return True, "Estoque atualizado."
