from .db import db_execute, jb_solucoes_db
from .service import PAGAMENTO_PAGO

# Enquanto o cliente analisa o orçamento, e depois que o serviço fecha, as peças não mudam
STATUS_QUE_MEXEM_EM_PECAS = ('Aberto', 'Reprovado', 'Aprovado')
MENSAGEM_ORCAMENTO_REABERTO = " O valor mudou: o orçamento voltou para o cliente aprovar de novo."
MENSAGEM_PECAS_TRAVADAS = "Não dá para mexer nas peças enquanto o cliente analisa o orçamento, nem em serviço já fechado."

# Diferença a receber na retirada: soma das peças lançadas depois que o cliente pagou pelo site
# (marcadas com cobrar_na_retirada = 1 no lançamento).
# "{servico}" é o nome (ou apelido) da tabela servicos na consulta que usa este trecho.
DIFERENCA_SQL = """(SELECT COALESCE(SUM(mp.quantidade * mp.preco_unitario), 0)
                    FROM manutencao_pecas mp JOIN manutencoes m ON m.id = mp.id_manutencao
                    WHERE m.id_servico = {servico}.id AND mp.cobrar_na_retirada = 1)"""


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
    def ajustar_estoque(id_estoque, quantidade, minimo=None, quantidade_vista=None):
        """
        Define a quantidade em estoque de uma peça em uma filial (contagem ou entrada de mercadoria)
        e, se vier, o estoque mínimo que dispara o aviso de repor.
        "quantidade_vista" é o número que a tela mostrava: se o estoque mudou depois (alguém usou
        a peça em um serviço), nada é gravado, para a tela velha não desfazer a baixa.
        """
        quantidade, minimo, erro = PecaModel._validar_quantidades(quantidade, minimo)
        if erro:
            return False, "Informe quantidades válidas (números inteiros, zero ou mais)."
        try:
            quantidade_vista = int(quantidade_vista)
        except (TypeError, ValueError):
            return False, "Recarregue a página e tente de novo."

        arg = "UPDATE estoque_pecas SET quantidade_atual=%s, quantidade_minima=%s WHERE id=%s AND quantidade_atual=%s;"
        res = db_execute(arg, quantidade, minimo, id_estoque, quantidade_vista)
        if not res[0]:
            return False, "Erro ao atualizar o estoque."
        if not res[1]:
            # Nenhuma linha mudou: ou nada foi alterado na tela, ou o estoque não é mais o que a tela mostrava
            atual = db_execute("SELECT quantidade_atual FROM estoque_pecas WHERE id=%s;", id_estoque, fetch_type="one")
            if not atual[0] or not atual[1] or atual[1][0] != quantidade_vista:
                return False, "O estoque dessa peça mudou enquanto a página estava aberta. Confira o número e salve de novo."
        return True, "Estoque atualizado."

    # === PEÇAS USADAS NA MANUTENÇÃO ===
    @staticmethod
    def _servico_para_mexer(c, condicao, valor):
        """
        Trava e devolve (id da manutenção, id do serviço, status) do serviço cujas peças vão mudar,
        ou uma mensagem de erro quando o serviço não aceita mudança nas peças.
        """
        c.execute(f"""
            SELECT m.id, s.id, s.status_servico, s.pagamento
            FROM servicos s JOIN manutencoes m ON m.id_servico = s.id
            WHERE {condicao} AND s.servico_solicitado = 'manutencao' FOR UPDATE;
        """, (valor,))
        linha = c.fetchone()
        if not linha or linha[2] not in STATUS_QUE_MEXEM_EM_PECAS:
            return None, MENSAGEM_PECAS_TRAVADAS
        return linha, None

    @staticmethod
    def _modo(status, pagamento, avisar_cliente):
        """
        Em serviço já aprovado, o colaborador escolhe o que acontece com o valor:
        - "manter": o valor combinado continua (a peça entra ou sai sem custo para o cliente);
        - "reabrir": o valor muda e o orçamento volta para o cliente aprovar;
        - "diferenca": o cliente já pagou pelo site, então a peça a mais vira uma diferença
          a receber na retirada (não dá para "despagar" o que já foi pago).
        Fora de serviço aprovado devolve None: a peça entra normalmente no próximo orçamento.
        """
        if status != 'Aprovado':
            return None
        if not avisar_cliente:
            return "manter"
        return "diferenca" if pagamento == PAGAMENTO_PAGO else "reabrir"

    @staticmethod
    def _reabrir_orcamento(c, id_servico, diferenca):
        """
        Peça que entra ou sai depois da aprovação muda o valor: o orçamento volta para o cliente
        aprovar de novo (e escolher o pagamento de novo).
        """
        c.execute("""
            UPDATE servicos
            SET valor_servico = GREATEST(valor_servico + %s, 0), status_servico = 'Aguardando Aprovação', pagamento = NULL
            WHERE id = %s;
        """, (diferenca, id_servico))

    @staticmethod
    def usar_na_manutencao(id_servico, id_estoque, quantidade, avisar_cliente=True):
        """
        Registra que uma manutenção usa uma peça e dá baixa no estoque,
        em uma única transação: ou grava tudo, ou não grava nada.
        O preço cobrado pela peça fica guardado no lançamento (preco_unitario): é o preço do dia,
        ou zero quando o serviço já estava aprovado e o colaborador escolheu manter o valor.
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
            servico, erro = PecaModel._servico_para_mexer(c, "s.id = %s", id_servico)
            if erro:
                conexao.rollback()
                return False, erro
            id_manutencao, _, status, pagamento = servico
            modo = PecaModel._modo(status, pagamento, avisar_cliente)

            # A baixa só acontece se houver peças suficientes (confere e desconta no mesmo comando)
            c.execute("UPDATE estoque_pecas SET quantidade_atual = quantidade_atual - %s WHERE id=%s AND quantidade_atual >= %s;",
                      (quantidade, id_estoque, quantidade))
            if not c.rowcount:
                conexao.rollback()
                return False, "Não há essa quantidade da peça em estoque."

            c.execute("SELECT p.preco_venda FROM estoque_pecas e JOIN pecas p ON p.id = e.id_peca WHERE e.id=%s;", (id_estoque,))
            preco = 0 if modo == "manter" else c.fetchone()[0]  # valor mantido: a peça não é cobrada do cliente
            c.execute("""
                INSERT INTO manutencao_pecas (quantidade, preco_unitario, cobrar_na_retirada, id_manutencao, id_estoque_peca)
                VALUES (%s, %s, %s, %s, %s);
            """, (quantidade, preco, 1 if modo == "diferenca" else 0, id_manutencao, id_estoque))
            mensagem = "Peça registrada no serviço e baixada do estoque."
            if modo == "manter":
                mensagem += " O valor do serviço foi mantido."
            elif modo == "reabrir":
                PecaModel._reabrir_orcamento(c, id_servico, quantidade * preco)
                mensagem += MENSAGEM_ORCAMENTO_REABERTO
            elif modo == "diferenca":
                mensagem += " O cliente já pagou pelo site: o valor desta peça fica como diferença a receber na retirada."
            conexao.commit()
            return True, mensagem
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return False, "Erro ao registrar a peça."
        finally:
            c.close()

    @staticmethod
    def remover_da_manutencao(id_uso, avisar_cliente=True):
        """Desfaz um "Usar peça" lançado errado: a peça volta para o estoque, em uma única transação."""
        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            servico, erro = PecaModel._servico_para_mexer(
                c, "m.id = (SELECT id_manutencao FROM manutencao_pecas WHERE id = %s)", id_uso)
            if erro:
                conexao.rollback()
                return False, erro
            _, id_servico, status, pagamento = servico
            modo = PecaModel._modo(status, pagamento, avisar_cliente)

            c.execute("SELECT quantidade, preco_unitario, id_estoque_peca, cobrar_na_retirada FROM manutencao_pecas WHERE id=%s;", (id_uso,))
            quantidade, preco, id_estoque, depois_do_pagamento = c.fetchone()
            # Peça que o cliente já pagou pelo site e não vai ser usada: o valor dela fica para devolver na retirada
            a_devolver = quantidade * preco if modo == "diferenca" and not depois_do_pagamento else 0
            if a_devolver:
                c.execute("UPDATE servicos SET valor_a_devolver = valor_a_devolver + %s WHERE id=%s;", (a_devolver, id_servico))

            c.execute("UPDATE estoque_pecas SET quantidade_atual = quantidade_atual + %s WHERE id=%s;", (quantidade, id_estoque))
            c.execute("DELETE FROM manutencao_pecas WHERE id=%s;", (id_uso,))
            mensagem = "Peça removida do serviço e devolvida ao estoque."
            if modo == "reabrir":
                PecaModel._reabrir_orcamento(c, id_servico, -quantidade * preco)
                mensagem += MENSAGEM_ORCAMENTO_REABERTO
            elif a_devolver:
                valor = f"{float(a_devolver):.2f}".replace(".", ",")
                mensagem += f" O cliente já tinha pago por ela: R$ {valor} ficam para devolver na retirada."
            elif pagamento == PAGAMENTO_PAGO and preco and depois_do_pagamento:
                mensagem += " A diferença a receber na retirada diminuiu."
            elif modo:
                mensagem += " O valor do serviço foi mantido."
            conexao.commit()
            return True, mensagem
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return False, "Erro ao remover a peça."
        finally:
            c.close()

    @staticmethod
    def diferencas():
        """
        Acerto a fazer na retirada, por serviço já pago pelo site: peças cobradas lançadas depois do
        pagamento (a receber) menos peças já pagas que foram removidas (a devolver).
        Entra no valor do serviço (e no caixa) quando a entrega é registrada.
        :return: dicionário {id do serviço: valor}. Positivo: o cliente paga a diferença.
                 Negativo: a loja devolve. Só traz os serviços que têm acerto.
        """
        arg = f"""
            SELECT s.id, {DIFERENCA_SQL.format(servico="s")} - s.valor_a_devolver
            FROM servicos s
            WHERE s.servico_solicitado = 'manutencao' AND s.pagamento = %s AND s.status_servico IN ('Aprovado', 'Concluído');
        """
        res = db_execute(arg, PAGAMENTO_PAGO, fetch_type="all")
        if not res[0] or not res[1]:
            return {}
        return {id_servico: valor for id_servico, valor in res[1] if valor}

    @staticmethod
    def devolver_do_encerrado(id_servico):
        """
        Serviço encerrado sem conserto (orçamento reprovado): as peças separadas voltam para o
        estoque e os lançamentos são apagados, em uma única transação.
        :return: quantos lançamentos foram desfeitos.
        """
        de_onde = """
            FROM manutencao_pecas mp
            JOIN manutencoes m ON m.id = mp.id_manutencao
            JOIN servicos s ON s.id = m.id_servico
            WHERE m.id_servico = %s AND s.status_servico = 'Encerrado'
        """
        conexao = jb_solucoes_db.connection
        c = conexao.cursor()
        try:
            # Soma por estoque antes: a mesma peça pode ter sido lançada mais de uma vez no serviço
            c.execute(f"""
                UPDATE estoque_pecas e
                JOIN (SELECT mp.id_estoque_peca, SUM(mp.quantidade) AS total {de_onde} GROUP BY mp.id_estoque_peca) d
                  ON d.id_estoque_peca = e.id
                SET e.quantidade_atual = e.quantidade_atual + d.total;
            """, (id_servico,))
            c.execute(f"DELETE mp {de_onde};", (id_servico,))
            desfeitos = c.rowcount
            conexao.commit()
            return desfeitos
        except Exception as e:
            conexao.rollback()
            print(e)  # Para depuração no terminal
            return 0
        finally:
            c.close()

    @staticmethod
    def total_do_servico(id_servico):
        """Soma as peças lançadas em um serviço, pelo preço guardado no lançamento (entra no valor do orçamento)."""
        arg = """
            SELECT COALESCE(SUM(mp.quantidade * mp.preco_unitario), 0)
            FROM manutencao_pecas mp
            JOIN manutencoes m ON m.id = mp.id_manutencao
            WHERE m.id_servico = %s;
        """
        res = db_execute(arg, id_servico, fetch_type="one")
        return float(res[1][0]) if res[0] and res[1] else 0.0

    @staticmethod
    def usadas_por_servico():
        """
        Peças lançadas nas manutenções que ainda não foram fechadas.
        :return: dicionário {id do serviço: {"itens": [{"id", "texto", "valor"}], "total": soma dos valores}}
        """
        arg = """
            SELECT m.id_servico, mp.id, mp.quantidade, p.nome, f.nome, mp.quantidade * mp.preco_unitario
            FROM manutencao_pecas mp
            JOIN manutencoes m ON m.id = mp.id_manutencao
            JOIN servicos s ON s.id = m.id_servico
            JOIN estoque_pecas e ON e.id = mp.id_estoque_peca
            JOIN pecas p ON p.id = e.id_peca
            JOIN filiais f ON f.id = e.id_filial
            WHERE s.status_servico IN ('Aberto', 'Aguardando Aprovação', 'Reprovado', 'Aprovado')
            ORDER BY mp.id;
        """
        res = db_execute(arg, fetch_type="all")
        usadas = {}
        if res[0] and res[1]:
            for id_servico, id_uso, quantidade, peca, filial, valor in res[1]:
                servico = usadas.setdefault(id_servico, {"itens": [], "total": 0})
                servico["itens"].append({"id": id_uso, "texto": f"{quantidade} x {peca} ({filial})", "valor": valor})
                servico["total"] += valor
        return usadas
