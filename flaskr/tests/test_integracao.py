"""
Testes de integração: abrem as telas e enviam os formulários como um navegador faria,
com rotas, models e banco funcionando juntos. Usam o banco jb_ferramentas_teste.
"""
import contextlib
import io
import os
import threading
import unittest

import MySQLdb

import main
from cadastrar_exemplos import cadastrar
from model.db import db_execute
from model.painel import PainelModel
from model.service import ServiceModel
from model.toolmodel import CATALOGO_EXEMPLOS

app = main.app
BANCO = app.config["MYSQL_DB"]

COMPRA = "Furadeira Parafusadeira 3/8 21V com Kit"
ALUGUEL = "Esmerilhadeira Angular 115 mm 710W"
PRECO_COMPRA = CATALOGO_EXEMPLOS[COMPRA]["preco"]
DIARIA = CATALOGO_EXEMPLOS[ALUGUEL]["preco"]


def setUpModule():
    """Cria o banco de teste do zero: estrutura, um cliente e as ferramentas de exemplo."""
    assert BANCO.endswith("_teste"), "Os testes só podem rodar em um banco de teste."

    conexao = MySQLdb.connect(
        host=app.config["MYSQL_HOST"], user=app.config["MYSQL_USER"],
        passwd=app.config["MYSQL_PASSWORD"], port=app.config["MYSQL_PORT"])
    c = conexao.cursor()
    c.execute(f"CREATE DATABASE IF NOT EXISTS {BANCO}")
    c.execute(f"USE {BANCO}")

    caminho = os.path.join(os.path.dirname(__file__), "..", "..", "database", "jb_ferramentas.sql")
    with open(caminho, encoding="utf-8") as arquivo:
        estrutura = "".join(linha for linha in arquivo if not linha.startswith("--"))
    for comando in estrutura.split(";\n"):
        if comando.strip():
            c.execute(comando)
    conexao.commit()
    conexao.close()

    with app.app_context():
        db_execute("INSERT INTO perfis (id, perfil) VALUES (1, 'Administrador');")
        db_execute("""
            INSERT INTO pessoas (id, nome, tipo, codigo, endereco, email, telefone)
            VALUES (1, 'Cliente Teste', 'pf', '52998224725', 'Rua A, 1', 'cliente@teste.com', '11999990000');
        """)
        with contextlib.redirect_stdout(io.StringIO()):  # esconde as mensagens do script
            cadastrar()


class TesteBase(unittest.TestCase):
    """Cada teste começa com um cliente logado (pessoa 1) e termina limpando o que gravou."""

    def setUp(self):
        app.config["WTF_CSRF_ENABLED"] = False
        self.cliente = app.test_client()
        with self.cliente.session_transaction() as sessao:
            sessao["logged_in"] = True
            sessao["user_name"] = "teste"
            sessao["user_code"] = 1

    def tearDown(self):
        for comando in (
            "DELETE FROM alugueis;", "DELETE FROM servico_ferramentas;", "DELETE FROM manutencoes;",
            "DELETE FROM servicos;", "UPDATE unidade_ferramentas SET status='em_estoque';",
            "DELETE FROM usuarios;", "DELETE FROM pessoas WHERE id <> 1;",
            "UPDATE pessoas SET nome='Cliente Teste' WHERE id = 1;",
        ):
            self.sql(comando)

    def sql(self, comando, *valores):
        with app.app_context():
            ok, resultado = db_execute(comando, *valores)
        self.assertTrue(ok, resultado)
        return resultado

    def id_ferramenta(self, modelo):
        return self.sql("SELECT id FROM ferramentas WHERE modelo=%s;", modelo)[0][0]

    def deixar_so_uma_unidade(self, id_ferramenta):
        self.sql("UPDATE unidade_ferramentas SET status='reservada' WHERE id_ferramenta=%s;", id_ferramenta)
        self.sql("UPDATE unidade_ferramentas SET status='em_estoque' WHERE id_ferramenta=%s LIMIT 1;", id_ferramenta)

    def carrinho(self):
        with self.cliente.session_transaction() as sessao:
            return sessao.get("carrinho", [])

    def texto(self, resposta):
        return resposta.get_data(as_text=True)


class TesteAcesso(TesteBase):

    def test_paginas_publicas_abrem(self):
        visitante = app.test_client()
        for rota in ("/", "/login", "/register", "/ferramentas"):
            self.assertEqual(visitante.get(rota).status_code, 200, rota)

    def test_paginas_fechadas_mandam_para_o_login(self):
        visitante = app.test_client()
        for rota in ("/loja", "/perfil", "/carrinho", "/manutencao", "/colaborador/graficos", "/apidocs/"):
            resposta = visitante.get(rota)
            self.assertEqual(resposta.status_code, 302, rota)
            self.assertIn("/login", resposta.headers["Location"], rota)

    def test_paginas_abrem_para_quem_esta_logado(self):
        for rota in ("/loja", "/perfil", "/carrinho", "/manutencao", "/colaborador/graficos",
                     "/colaborador/ferramentas", "/admin/filiais", "/admin/perfis"):
            self.assertEqual(self.cliente.get(rota).status_code, 200, rota)

    def test_formulario_sem_token_csrf_e_recusado(self):
        app.config["WTF_CSRF_ENABLED"] = True
        self.cliente.post("/perfil", data={"nome": "Invasor", "email": "x@x.com"})
        self.assertEqual(self.sql("SELECT nome FROM pessoas WHERE id=1;")[0][0], "Cliente Teste")

    def test_detalhe_de_ferramenta_que_nao_existe_da_404(self):
        self.assertEqual(self.cliente.get("/detalhe/99999").status_code, 404)

    def test_upload_do_orcamento_recusa_arquivo_que_nao_e_imagem(self):
        self.cliente.post("/colaborador/orcamento/1", content_type="multipart/form-data",
                          data={"imagem_dano": (io.BytesIO(b"<script>"), "pagina.html")})
        self.assertNotIn("manutencao_dano_1_pagina.html", os.listdir(app.config["UPLOAD_FOLDER"]))


class TesteCadastroELogin(TesteBase):

    DADOS = {"nome": "Maria Teste", "tipo": "pf", "code": "111.444.777-35", "endereco": "Rua B, 2",
             "email": "maria@teste.com", "telefone": "(11) 98888-7777", "usuario": "maria", "senha": "segredo123"}

    def test_cadastro_cria_a_conta_e_o_login_funciona(self):
        visitante = app.test_client()
        self.assertIn("Cadastro realizado com sucesso", self.texto(visitante.post("/register", data=self.DADOS)))
        # O CPF é guardado só com números, e a senha nunca é guardada como foi digitada
        codigo, senha = self.sql("""
            SELECT p.codigo, u.senha FROM pessoas p JOIN usuarios u ON u.id_pessoa = p.id
            WHERE u.nome_usuario = 'maria';
        """)[0]
        self.assertEqual(codigo, "11144477735")
        self.assertNotEqual(senha, "segredo123")

        errado = visitante.post("/login", data={"usuario": "maria", "senha": "outra"})
        self.assertIn("Usuário ou senha incorretos", self.texto(errado))
        certo = visitante.post("/login", data={"usuario": "maria", "senha": "segredo123"})
        self.assertEqual(certo.status_code, 302)
        self.assertEqual(visitante.get("/perfil").status_code, 200)

    def test_cpf_invalido_nao_grava_nada(self):
        resposta = app.test_client().post("/register", data={**self.DADOS, "code": "111.444.777-36"})
        self.assertIn("CPF inválido", self.texto(resposta))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM pessoas;")[0][0], 1)

    def test_cpf_repetido_e_recusado_mesmo_sem_pontuacao(self):
        resposta = app.test_client().post("/register", data={**self.DADOS, "code": "52998224725"})
        self.assertIn("CPF/CNPJ já cadastrado", self.texto(resposta))

    def test_usuario_repetido_nao_deixa_pessoa_sem_conta(self):
        visitante = app.test_client()
        visitante.post("/register", data=self.DADOS)
        resposta = visitante.post("/register", data={**self.DADOS, "code": "11.222.333/0001-81", "tipo": "pj"})
        self.assertIn("já está em uso", self.texto(resposta))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM pessoas;")[0][0], 2)  # cliente de teste + Maria


class TestePerfilEManutencao(TesteBase):

    def test_salvar_perfil_grava_no_banco(self):
        self.cliente.post("/perfil", data={"nome": "Nome Novo", "email": "novo@teste.com",
                                           "telefone": "1133334444", "endereco": "Rua C, 3"})
        self.assertEqual(self.sql("SELECT nome, email, codigo FROM pessoas WHERE id=1;")[0],
                         ("Nome Novo", "novo@teste.com", "52998224725"))
        self.sql("UPDATE pessoas SET email='cliente@teste.com', telefone='11999990000', endereco='Rua A, 1' WHERE id=1;")

    def test_pedido_de_manutencao_e_gravado(self):
        self.cliente.post("/manutencao", data={"detalhes_equipamento": "Furadeira X", "descricao": "Não liga"})
        self.assertEqual(self.sql("""
            SELECT s.servico_solicitado, s.descricao_servico, m.diagnostico
            FROM servicos s JOIN manutencoes m ON m.id_servico = s.id;
        """), (("manutencao", "Não liga", "Furadeira X"),))


class TesteCarrinho(TesteBase):

    def setUp(self):
        super().setUp()
        self.compra = self.id_ferramenta(COMPRA)
        self.aluguel = self.id_ferramenta(ALUGUEL)

    def test_total_e_calculado_no_servidor(self):
        self.cliente.post(f"/carrinho/adicionar/{self.compra}")
        # valor_total falso é ignorado; 999 dias vira o máximo de 30
        self.cliente.post(f"/carrinho/adicionar/{self.aluguel}", data={"dias_aluguel": "999", "valor_total": "0.01"})
        pagina = self.texto(self.cliente.get("/carrinho"))
        self.assertIn(main.formatar_moeda(PRECO_COMPRA + DIARIA * 30), pagina)

    def test_remover_item(self):
        self.cliente.post(f"/carrinho/adicionar/{self.compra}")
        self.cliente.post(f"/carrinho/adicionar/{self.aluguel}", data={"dias_aluguel": "2"})
        self.cliente.post("/carrinho/remover/0")
        self.cliente.post("/carrinho/remover/99")  # posição que não existe: não faz nada
        self.assertEqual(self.carrinho(), [{"id": self.aluguel, "dias": 2}])

    def test_finalizar_grava_os_pedidos_e_da_baixa_no_estoque(self):
        self.cliente.post(f"/carrinho/adicionar/{self.compra}")
        self.cliente.post(f"/carrinho/adicionar/{self.aluguel}", data={"dias_aluguel": "3"})
        resposta = self.cliente.post("/carrinho/finalizar")

        self.assertIn("/perfil", resposta.headers["Location"])
        self.assertEqual(self.carrinho(), [])
        pedidos = self.sql("SELECT servico_solicitado, valor_servico FROM servicos ORDER BY id;")
        self.assertEqual([(tipo, float(valor)) for tipo, valor in pedidos],
                         [("venda", PRECO_COMPRA), ("aluguel", DIARIA * 3)])
        self.assertEqual(self.sql("SELECT status FROM unidade_ferramentas WHERE status <> 'em_estoque' ORDER BY status;"),
                         (("alugada",), ("baixada",)))
        self.assertEqual(self.sql("SELECT DATEDIFF(data_devolucao, NOW()) FROM alugueis;")[0][0], 3)
        # O pedido aparece no histórico do perfil e nos números do painel
        self.assertIn(COMPRA, self.texto(self.cliente.get("/perfil")))
        with app.app_context():
            self.assertEqual(PainelModel.get_resumo_mensal()["faturamento_total"], PRECO_COMPRA + DIARIA * 3)

    def test_item_esgotado_continua_no_carrinho(self):
        self.deixar_so_uma_unidade(self.compra)
        self.cliente.post(f"/carrinho/adicionar/{self.compra}")
        self.cliente.post(f"/carrinho/adicionar/{self.compra}")
        resposta = self.cliente.post("/carrinho/finalizar")

        self.assertIn("/carrinho", resposta.headers["Location"])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM servicos;")[0][0], 1)
        self.assertEqual(len(self.carrinho()), 1)

    def test_comprar_agora_nao_mexe_no_carrinho(self):
        self.cliente.post(f"/carrinho/adicionar/{self.aluguel}", data={"dias_aluguel": "2"})
        self.cliente.post(f"/carrinho/adicionar/{self.compra}", data={"agora": "1"})
        self.assertEqual(self.sql("SELECT servico_solicitado FROM servicos;"), (("venda",),))
        self.assertEqual(len(self.carrinho()), 1)

    def test_produto_esgotado_nao_mostra_botao_de_compra(self):
        self.sql("UPDATE unidade_ferramentas SET status='baixada' WHERE id_ferramenta=%s;", self.compra)
        pagina = self.texto(self.cliente.get(f"/detalhe/{self.compra}"))
        self.assertIn("Esgotado no momento", pagina)
        self.assertNotIn("Comprar agora", pagina)


class TesteEstoque(TesteBase):

    def test_duas_compras_ao_mesmo_tempo_nao_levam_a_mesma_unidade(self):
        ferramenta = self.id_ferramenta(COMPRA)
        self.deixar_so_uma_unidade(ferramenta)
        resultados = []

        def comprar():
            with app.app_context():
                resultados.append(ServiceModel.create_purchase(1, ferramenta, PRECO_COMPRA))

        compradores = [threading.Thread(target=comprar) for _ in range(2)]
        for comprador in compradores:
            comprador.start()
        for comprador in compradores:
            comprador.join()

        # Um compra; o outro recebe o aviso de esgotado (e não um erro do banco)
        self.assertEqual(sorted(mensagem for _, mensagem in resultados),
                         ["Compra realizada com sucesso!", "Desculpe, ferramenta esgotada em nosso estoque físico."])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM servicos;")[0][0], 1)

    def test_erro_no_meio_do_pedido_nao_grava_nada(self):
        ferramenta = self.id_ferramenta(ALUGUEL)
        with app.app_context(), contextlib.redirect_stdout(io.StringIO()):
            # dias="abc" faz o INSERT em alugueis falhar depois do INSERT em servicos
            resultado = ServiceModel._registrar_pedido("aluguel", "t", "t", 10, 1, ferramenta, "alugada", dias="abc")
        self.assertFalse(resultado)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM servicos;")[0][0], 0)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM unidade_ferramentas WHERE status <> 'em_estoque';")[0][0], 0)


if __name__ == "__main__":
    unittest.main()
