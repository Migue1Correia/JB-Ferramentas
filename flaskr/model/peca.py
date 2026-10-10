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
    def get(id_peca):
        """Busca os dados de uma peça (sem o estoque). None se não existir."""
        res = db_execute("SELECT id, codigo_barras, nome, fabricante, custo, preco_venda FROM pecas WHERE id=%s;",
                         id_peca, fetch_type="one")
        if not res[0] or res[1] is None:
            return None
        l = res[1]
        return {"id": l[0], "codigo": l[1], "nome": l[2], "fabricante": l[3], "custo": l[4], "preco": l[5]}

    @staticmethod
    def _validar_dados(codigo_barras, nome, fabricante, custo, preco_venda):
        """Confere os dados da peça. Devolve (custo, preço, mensagem de erro ou None)."""
        if not codigo_barras or not nome or not fabricante:
            return None, None, "Preencha código de barras, nome e fabricante."
        if len(codigo_barras) > 20 or len(nome) > 100 or len(fabricante) > 100:
            return None, None, "Código de barras com até 20 caracteres; nome e fabricante com até 100."
        try:
            custo, preco_venda = float(custo), float(preco_venda)
        except (TypeError, ValueError):
            return None, None, "Informe números válidos para custo e preço."
        if min(custo, preco_venda) < 0:
            return None, None, "Custo e preço não podem ser negativos."
        return custo, preco_venda, None

    @staticmethod
    def _validar_quantidades(quantidade, minimo):
        """Devolve (quantidade, mínimo, mensagem de erro ou None)."""
        try:
            quantidade, minimo = int(quantidade), int(minimo)
        except (TypeError, ValueError):
            return None, None, "Informe números inteiros para as quantidades."
        if min(quantidade, minimo) < 0:
            return None, None, "As quantidades não podem ser negativas."
        return quantidade, minimo, None

    @staticmethod
    def criar(codigo_barras, nome, fabricante, custo, preco_venda, id_filial, quantidade, minimo):
        """
        Cadastra uma peça e o estoque dela na filial, em uma única transação.
        """
        if not id_filial:
            return False, "Escolha a filial."
        custo, preco_venda, erro = PecaModel._validar_dados(codigo_barras, nome, fabricante, custo, preco_venda)
        if not erro:
            quantidade, minimo, erro = PecaModel._validar_quantidades(quantidade, minimo)
        if erro:
            return False, erro

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
    def atualizar(id_peca, codigo_barras, nome, fabricante, custo, preco_venda):
        """Altera os dados de uma peça. O estoque é ajustado na lista de peças."""
        custo, preco_venda, erro = PecaModel._validar_dados(codigo_barras, nome, fabricante, custo, preco_venda)
        if erro:
            return False, erro
        res = db_execute("UPDATE pecas SET codigo_barras=%s, nome=%s, fabricante=%s, custo=%s, preco_venda=%s WHERE id=%s;",
                         codigo_barras, nome, fabricante, custo, preco_venda, id_peca)
        if not res[0]:
            if "Duplicate" in str(res[1]):
                return False, "Esse código de barras já existe em outra peça."
            return False, "Erro ao alterar a peça."
        return True, "Peça alterada com sucesso!"

    @staticmethod
    def por_em_filial(id_peca, id_filial, quantidade, minimo):
        """Abre o estoque de uma peça já cadastrada em mais uma filial."""
        quantidade, minimo, erro = PecaModel._validar_quantidades(quantidade, minimo)
        if erro:
            return False, erro
        ja_tem = db_execute("SELECT id FROM estoque_pecas WHERE id_peca=%s AND id_filial=%s;", id_peca, id_filial, fetch_type="one")
        if ja_tem[0] and ja_tem[1]:
            return False, "Essa peça já tem estoque nessa filial. Ajuste a quantidade na lista de peças."
        res = db_execute("INSERT INTO estoque_pecas (id_peca, id_filial, quantidade_atual, quantidade_minima) VALUES (%s, %s, %s, %s);",
                         id_peca, id_filial, quantidade, minimo)
        if not res[0]:
            return False, "Erro ao colocar a peça na filial. Confira a filial escolhida."
        return True, "Peça colocada na filial."

    @staticmethod
    def excluir(id_peca):
        """
        Apaga a peça e o estoque dela, em uma única transação. Peça já usada em alguma
        manutenção não é apagada: o banco recusa (chave estrangeira), para o histórico não se perder.
        """
        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            c.execute("DELETE FROM estoque_pecas WHERE id_peca=%s;", (id_peca,))
            c.execute("DELETE FROM pecas WHERE id=%s;", (id_peca,))
            conexao.commit()
            return True, "Peça excluída."
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return False, "Essa peça já foi usada em uma manutenção e não pode ser excluída."
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

    # === PEÇAS USADAS NA MANUTENÇÃO ===
    @staticmethod
    def usar_na_manutencao(id_servico, id_estoque, quantidade):
        """
        Registra que uma manutenção aprovada usou uma peça e dá baixa no estoque,
        em uma única transação: ou grava os dois, ou não grava nada.
        """
        try:
            quantidade = int(quantidade)
        except (TypeError, ValueError):
            quantidade = 0
        if quantidade < 1 or not id_estoque:
            return False, "Escolha a peça e informe a quantidade (1 ou mais)."

        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            c.execute("""
                SELECT m.id FROM manutencoes m JOIN servicos s ON s.id = m.id_servico
                WHERE s.id=%s AND s.servico_solicitado='manutencao' AND s.status_servico='Aprovado';
            """, (id_servico,))
            manutencao = c.fetchone()
            if not manutencao:
                conexao.rollback()
                return False, "Só dá para usar peça em manutenção com orçamento aprovado."

            # A baixa só acontece se houver peças suficientes (confere e desconta no mesmo comando)
            c.execute("UPDATE estoque_pecas SET quantidade_atual = quantidade_atual - %s WHERE id=%s AND quantidade_atual >= %s;",
                      (quantidade, id_estoque, quantidade))
            if not c.rowcount:
                conexao.rollback()
                return False, "Não há essa quantidade da peça em estoque."

            c.execute("INSERT INTO manutencao_pecas (quantidade, id_manutencao, id_estoque_peca) VALUES (%s, %s, %s);",
                      (quantidade, manutencao[0], id_estoque))
            conexao.commit()
            return True, "Peça registrada no serviço e baixada do estoque."
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return False, "Erro ao registrar a peça."
        finally:
            c.close()

    @staticmethod
    def usadas_por_servico():
        """
        Peças já usadas nas manutenções aprovadas (em reparo).
        :return: dicionário {id do serviço: ["2 x Escova de carvão (Matriz)", ...]}
        """
        arg = """
            SELECT m.id_servico, mp.quantidade, p.nome, f.nome
            FROM manutencao_pecas mp
            JOIN manutencoes m ON m.id = mp.id_manutencao
            JOIN servicos s ON s.id = m.id_servico
            JOIN estoque_pecas e ON e.id = mp.id_estoque_peca
            JOIN pecas p ON p.id = e.id_peca
            JOIN filiais f ON f.id = e.id_filial
            WHERE s.status_servico = 'Aprovado'
            ORDER BY mp.id;
        """
        res = db_execute(arg, fetch_type="all")
        usadas = {}
        if res[0] and res[1]:
            for id_servico, quantidade, peca, filial in res[1]:
                usadas.setdefault(id_servico, []).append(f"{quantidade} x {peca} ({filial})")
        return usadas
