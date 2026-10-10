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
from werkzeug.datastructures import FileStorage

import main
from cadastrar_exemplos import cadastrar, FERRAMENTAS
from model.db import db_execute
from model.painel import PainelModel
from model.service import ServiceModel

app = main.app
BANCO = app.config["MYSQL_DB"]

COMPRA = "Furadeira Parafusadeira 3/8 21V com Kit"
ALUGUEL = "Esmerilhadeira Angular 115 mm 710W"
PRECOS = {modelo: preco for _, modelo, _, preco, _, _ in FERRAMENTAS}
PRECO_COMPRA = PRECOS[COMPRA]
DIARIA = PRECOS[ALUGUEL]


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
    """Cada teste começa com o usuário "teste" (Administrador, pessoa 1) logado e termina limpando o que gravou."""

    def setUp(self):
        app.config["WTF_CSRF_ENABLED"] = False
        main.TENTATIVAS_DE_LOGIN.clear()
        self.sql("INSERT INTO usuarios (nome_usuario, senha, id_pessoa, id_perfil, ativo) VALUES ('teste', 'x', 1, 1, 1);")
        self.cliente = app.test_client()
        with self.cliente.session_transaction() as sessao:
            sessao["logged_in"] = True
            sessao["user_name"] = "teste"
            sessao["user_code"] = 1
            sessao["perfil"] = "Administrador"

    def tearDown(self):
        for comando in (
            "DELETE FROM alugueis;", "DELETE FROM servico_ferramentas;", "DELETE FROM manutencoes;",
            "DELETE FROM servicos;", "UPDATE unidade_ferramentas SET status='em_estoque';",
            "DELETE FROM usuarios;", "DELETE FROM pessoas WHERE id <> 1;", "DELETE FROM perfis WHERE id <> 1;",
            "UPDATE pessoas SET nome='Cliente Teste' WHERE id = 1;",
        ):
            self.sql(comando)

    def sql(self, comando, *valores):
        with app.app_context():
            ok, resultado = db_execute(comando, *valores)
        self.assertTrue(ok, resultado)
        return resultado

    def definir_perfil(self, perfil, usuario="teste"):
        """Troca o perfil de um usuário direto no banco (criando o perfil, se preciso)."""
        if not self.sql("SELECT id FROM perfis WHERE perfil=%s;", perfil):
            self.sql("INSERT INTO perfis (perfil) VALUES (%s);", perfil)
        self.sql("UPDATE usuarios SET id_perfil=(SELECT id FROM perfis WHERE perfil=%s) WHERE nome_usuario=%s;", perfil, usuario)

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
                     "/colaborador/ferramentas", "/colaborador/painel", "/colaborador/financeiro",
                     "/admin/filiais", "/admin/perfis"):
            self.assertEqual(self.cliente.get(rota).status_code, 200, rota)

    def test_toda_tela_mostra_o_aviso_pendente(self):
        # Se alguma tela não mostrasse, o aviso ficaria guardado e apareceria atrasado em outra
        ferramenta = self.id_ferramenta(COMPRA)
        for rota in ("/", "/login", "/register", "/ferramentas", "/loja", f"/detalhe/{ferramenta}", "/carrinho",
                     "/perfil", "/manutencao", "/colaborador/graficos", "/colaborador/ferramentas",
                     "/colaborador/painel", "/colaborador/financeiro",
                     "/admin/filiais", "/admin/perfis"):
            with self.cliente.session_transaction() as sessao:
                sessao["_flashes"] = [("success", "AVISO DE TESTE")]
            self.assertIn("AVISO DE TESTE", self.texto(self.cliente.get(rota)), rota)

    def test_perfil_que_nao_esta_na_lista_e_tratado_como_cliente(self):
        for perfil in ("Cliente", "Cliente VIP", "Gerente"):
            self.definir_perfil(perfil)
            self.assertEqual(self.cliente.get("/colaborador/financeiro").status_code, 302, perfil)
        self.definir_perfil("Colaborador")
        self.assertEqual(self.cliente.get("/colaborador/financeiro").status_code, 200)

    def test_card_manutencao_leva_o_colaborador_para_servicos_e_o_cliente_para_o_pedido(self):
        card = '<a href="{}" style="text-decoration: none; color: inherit; display: block; flex: 1;">'
        for rota in ("/ferramentas", "/loja", "/perfil", "/manutencao"):
            self.assertIn(card.format("/colaborador/painel"), self.texto(self.cliente.get(rota)), rota)
        self.definir_perfil("Cliente")
        self.cliente.get("/colaborador/painel")  # o acesso negado atualiza o perfil guardado na sessão
        for rota in ("/ferramentas", "/loja", "/perfil", "/manutencao"):
            self.assertIn(card.format("/manutencao"), self.texto(self.cliente.get(rota)), rota)

    def test_quem_perde_o_perfil_perde_o_acesso_sem_precisar_sair(self):
        self.assertEqual(self.cliente.get("/colaborador/financeiro").status_code, 200)
        self.definir_perfil("Cliente")  # rebaixado no banco, com a sessão ainda aberta
        self.assertEqual(self.cliente.get("/colaborador/financeiro").status_code, 302)
        self.assertNotIn("Gráficos de vendas", self.texto(self.cliente.get("/loja")))

    def test_sair_so_funciona_por_formulario(self):
        self.assertEqual(self.cliente.get("/logout").status_code, 405)  # link ou imagem de outro site não desloga
        self.cliente.post("/logout")
        self.assertIn("/login", self.cliente.get("/perfil").headers["Location"])

    def test_fotos_com_o_mesmo_nome_nao_se_sobrescrevem(self):
        caminhos = [main.salvar_imagem(FileStorage(io.BytesIO(b"x"), filename="foto.png"), "teste") for _ in range(2)]
        self.assertNotEqual(caminhos[0], caminhos[1])
        for caminho in caminhos:
            os.remove(os.path.join(app.static_folder, caminho))

    def test_foto_maior_que_5_mb_e_recusada(self):
        resposta = self.cliente.post("/colaborador/ferramentas", content_type="multipart/form-data",
                                     data={"imagem": (io.BytesIO(b"x" * (5 * 1024 * 1024 + 1)), "grande.png")})
        self.assertEqual(resposta.status_code, 413)
        resposta.close()

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
        # O aviso aparece já na página para onde o login leva, e não numa tela seguinte
        self.assertIn("Login realizado com sucesso!", self.texto(visitante.get(certo.headers["Location"])))
        self.assertEqual(visitante.get("/perfil").status_code, 200)

        # Quem se cadastra pelo site é Cliente: não entra nas telas de colaborador nem vê o card do painel
        self.assertEqual(self.sql("""
            SELECT p.perfil FROM usuarios u JOIN perfis p ON p.id = u.id_perfil WHERE u.nome_usuario = 'maria';
        """)[0][0], "Cliente")
        for rota in ("/colaborador/graficos", "/colaborador/financeiro", "/admin/perfis", "/apidocs/"):
            self.assertEqual(visitante.get(rota).status_code, 302, rota)
        self.assertNotIn("Gráficos de vendas", self.texto(visitante.get("/loja")))

    def test_administrador_entra_nas_telas_de_colaborador(self):
        self.sql("INSERT INTO usuarios (nome_usuario, senha, id_pessoa, id_perfil, ativo) VALUES ('chefe', %s, 1, 1, 1);",
                 main.jb_bcrypt.generate_password_hash("senha-do-chefe").decode("utf-8"))
        visitante = app.test_client()
        visitante.post("/login", data={"usuario": "chefe", "senha": "senha-do-chefe"})
        self.assertEqual(visitante.get("/colaborador/graficos").status_code, 200)
        self.assertIn("Gráficos de vendas", self.texto(visitante.get("/loja")))

    def test_administrador_troca_o_perfil_de_outro_usuario(self):
        app.test_client().post("/register", data=self.DADOS)
        maria = self.sql("SELECT id FROM usuarios WHERE nome_usuario='maria';")[0][0]
        perfil_de = lambda usuario: self.sql("SELECT p.perfil FROM usuarios u JOIN perfis p ON p.id=u.id_perfil WHERE u.nome_usuario=%s;", usuario)[0][0]

        # Colaborador que não é Administrador não consegue
        self.definir_perfil("Colaborador")
        self.cliente.post(f"/admin/usuarios/{maria}/perfil", data={"id_perfil": 1})
        self.assertEqual(perfil_de("maria"), "Cliente")

        # Administrador consegue
        self.definir_perfil("Administrador")
        self.cliente.post(f"/admin/usuarios/{maria}/perfil", data={"id_perfil": 1})
        self.assertEqual(perfil_de("maria"), "Administrador")

    def test_administrador_nao_troca_o_proprio_perfil_nem_logando_em_maiusculas(self):
        self.sql("UPDATE usuarios SET senha=%s WHERE nome_usuario='teste';",
                 main.jb_bcrypt.generate_password_hash("senha-de-teste").decode("utf-8"))
        visitante = app.test_client()
        visitante.post("/login", data={"usuario": "TESTE", "senha": "senha-de-teste"})
        with visitante.session_transaction() as sessao:
            self.assertEqual(sessao["user_name"], "teste")  # guardado como está no banco
        self.definir_perfil("Cliente", usuario="ninguem")   # só garante que o perfil Cliente existe
        cliente = self.sql("SELECT id FROM perfis WHERE perfil='Cliente';")[0][0]
        eu = self.sql("SELECT id FROM usuarios WHERE nome_usuario='teste';")[0][0]
        visitante.post(f"/admin/usuarios/{eu}/perfil", data={"id_perfil": cliente})
        self.assertEqual(self.sql("SELECT id_perfil FROM usuarios WHERE id=%s;", eu)[0][0], 1)

    def test_login_sem_senha_nao_quebra(self):
        resposta = app.test_client().post("/login", data={"usuario": "teste"})
        self.assertIn("Usuário ou senha incorretos", self.texto(resposta))

    def test_login_bloqueia_depois_de_cinco_erros(self):
        self.sql("UPDATE usuarios SET senha=%s WHERE nome_usuario='teste';",
                 main.jb_bcrypt.generate_password_hash("senha-de-teste").decode("utf-8"))
        visitante = app.test_client()
        for _ in range(5):
            visitante.post("/login", data={"usuario": "teste", "senha": "errada"})
        resposta = visitante.post("/login", data={"usuario": "Teste", "senha": "senha-de-teste"})  # senha certa, mas bloqueado
        self.assertIn("Muitas tentativas", self.texto(resposta))

    def test_cliente_nao_envia_formulario_de_colaborador(self):
        self.definir_perfil("Cliente")
        self.cliente.post("/admin/filiais", data={"codigo_filial": "XX", "nome": "Invasão", "endereco": "x"})
        self.assertEqual(self.sql("SELECT COUNT(*) FROM filiais WHERE codigo_filial='XX';")[0][0], 0)

    def test_senha_curta_e_recusada(self):
        resposta = app.test_client().post("/register", data={**self.DADOS, "senha": "1234567"})
        self.assertIn("pelo menos 8 caracteres", self.texto(resposta))
        self.assertEqual(self.sql("SELECT COUNT(*) FROM pessoas;")[0][0], 1)

    def test_login_nao_herda_o_carrinho_de_quem_usou_antes(self):
        app.test_client().post("/register", data=self.DADOS)
        self.cliente.post(f"/carrinho/adicionar/{self.id_ferramenta(COMPRA)}")
        self.assertEqual(len(self.carrinho()), 1)
        self.cliente.post("/login", data={"usuario": "maria", "senha": "segredo123"})
        self.assertEqual(self.carrinho(), [])

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

    def test_perfil_nao_apaga_telefone_nem_endereco(self):
        resposta = self.cliente.post("/perfil", follow_redirects=True,
                                     data={"nome": "Nome Novo", "email": "novo@teste.com", "telefone": "", "endereco": ""})
        self.assertIn("Preencha nome, e-mail, telefone e endereço", self.texto(resposta))
        self.assertEqual(self.sql("SELECT nome FROM pessoas WHERE id=1;")[0][0], "Cliente Teste")

    def test_manutencao_sem_o_equipamento_nao_grava_nada(self):
        self.cliente.post("/manutencao", data={"descricao": "Não liga"})
        self.assertEqual(self.sql("SELECT COUNT(*) FROM servicos;")[0][0], 0)

    def test_pedido_de_manutencao_e_gravado(self):
        self.cliente.post("/manutencao", data={"detalhes_equipamento": "Furadeira X", "descricao": "Não liga"})
        self.assertEqual(self.sql("""
            SELECT s.servico_solicitado, s.descricao_servico, m.diagnostico
            FROM servicos s JOIN manutencoes m ON m.id_servico = s.id;
        """), (("manutencao", "Não liga", "Furadeira X"),))


class TesteOrcamentoECaixa(TesteBase):

    def test_manutencao_passa_pelo_orcamento_e_entra_no_caixa(self):
        self.cliente.post("/manutencao", data={"detalhes_equipamento": "Furadeira X", "descricao": "Não liga"})
        servico = self.sql("SELECT id FROM servicos;")[0][0]

        # 1. O colaborador vê o pedido e manda o orçamento
        self.assertIn("Não liga", self.texto(self.cliente.get("/colaborador/painel")))
        self.assertIn("1 aguardando orçamento da oficina", self.texto(self.cliente.get("/manutencao")))
        self.cliente.post(f"/colaborador/orcamento/{servico}", data={
            "valor_servico": "120.50", "status_servico": "Aguardando Aprovação", "detalhes_dano": "Escova gasta"})
        self.assertEqual(self.sql("SELECT status_servico, valor_servico FROM servicos;")[0][0], "Aguardando Aprovação")
        self.assertEqual(self.sql("SELECT diagnostico FROM manutencoes;")[0][0], "Escova gasta")

        # 2. Ainda não aprovado: não conta no caixa, e o cliente vê o botão de aprovar
        self.assertIn("Nenhum serviço aprovado", self.texto(self.cliente.get("/colaborador/financeiro")))
        self.assertIn("Aprovar", self.texto(self.cliente.get("/perfil")))
        self.assertIn("1 aguardando a sua aprovação", self.texto(self.cliente.get("/manutencao")))

        # 3. O cliente aprova: entra no caixa e sai da lista de pendentes
        self.cliente.post(f"/cliente/orcamento/{servico}/Aprovado", data={"pagamento": "retirada"})
        self.assertIn(main.formatar_moeda(120.50), self.texto(self.cliente.get("/colaborador/financeiro")))
        self.assertIn("Nenhum serviço pendente", self.texto(self.cliente.get("/colaborador/painel")))
        self.assertIn("1 aprovado(s), em reparo", self.texto(self.cliente.get("/manutencao")))

        # 4. O colaborador conclui: aparece como pronto para retirada
        self.cliente.post(f"/colaborador/servico/{servico}/fechar")
        pagina = self.texto(self.cliente.get("/manutencao"))
        self.assertIn("1 equipamento(s) pronto(s)", pagina)
        self.assertIn("Nenhum pedido em andamento", pagina)

    def abrir_manutencao(self):
        self.cliente.post("/manutencao", data={"detalhes_equipamento": "Furadeira X", "descricao": "Não liga"})
        return self.sql("SELECT MAX(id) FROM servicos;")[0][0]

    def test_orcamento_nao_altera_uma_venda(self):
        self.cliente.post(f"/carrinho/adicionar/{self.id_ferramenta(COMPRA)}", data={"agora": "1"})
        venda = self.sql("SELECT id FROM servicos;")[0][0]
        self.cliente.post(f"/colaborador/orcamento/{venda}", data={
            "valor_servico": "0", "status_servico": "Aguardando Aprovação", "detalhes_dano": "x"})
        status, valor = self.sql("SELECT status_servico, valor_servico FROM servicos;")[0]
        self.assertEqual((status, float(valor)), ("Concluído", PRECO_COMPRA))

    def test_orcamento_recusa_valor_negativo(self):
        servico = self.abrir_manutencao()
        self.cliente.post(f"/colaborador/orcamento/{servico}", data={
            "valor_servico": "-100", "status_servico": "Concluído", "detalhes_dano": "x"})
        status, valor = self.sql("SELECT status_servico, valor_servico FROM servicos;")[0]
        self.assertEqual((status, float(valor)), ("Aberto", 0.0))

    def test_colaborador_ve_a_resposta_do_cliente_e_fecha_o_servico(self):
        for resposta, final, no_caixa in (("Reprovado", "Encerrado", False), ("Aprovado", "Concluído", True)):
            servico = self.abrir_manutencao()
            self.cliente.post(f"/colaborador/orcamento/{servico}", data={
                "valor_servico": "120", "status_servico": "Aguardando Aprovação", "detalhes_dano": "x"})
            self.cliente.post(f"/cliente/orcamento/{servico}/{resposta}", data={"pagamento": "retirada"})

            # aparece para o colaborador com a resposta do cliente
            pagina = self.texto(self.cliente.get("/colaborador/painel"))
            self.assertIn(f"<strong>{resposta}</strong>", pagina)

            self.cliente.post(f"/colaborador/servico/{servico}/fechar")
            self.assertEqual(self.sql("SELECT status_servico FROM servicos WHERE id=%s;", servico)[0][0], final)
            self.assertIn("Nenhum orçamento respondido", self.texto(self.cliente.get("/colaborador/painel")))
            self.assertEqual(main.formatar_moeda(120) in self.texto(self.cliente.get("/colaborador/financeiro")), no_caixa)

    def test_orcamento_recusa_status_inventado(self):
        servico = self.abrir_manutencao()
        self.cliente.post(f"/colaborador/orcamento/{servico}", data={
            "valor_servico": "50", "status_servico": "Qualquer Coisa", "detalhes_dano": "x"})
        self.assertEqual(self.sql("SELECT status_servico FROM servicos;")[0][0], "Aberto")

    def test_orcamento_reprovado_fica_fora_do_caixa_e_do_painel(self):
        servico = self.abrir_manutencao()
        self.cliente.post(f"/colaborador/orcamento/{servico}", data={
            "valor_servico": "120", "status_servico": "Aguardando Aprovação", "detalhes_dano": "x"})
        self.cliente.post(f"/cliente/orcamento/{servico}/Reprovado")
        self.assertEqual(self.sql("SELECT status_servico FROM servicos;")[0][0], "Reprovado")
        self.assertIn("Nenhum serviço aprovado", self.texto(self.cliente.get("/colaborador/financeiro")))
        with app.app_context():
            self.assertEqual(PainelModel.get_resumo_mensal()["faturamento_total"], 0)

    def test_cliente_nao_responde_orcamento_de_outra_pessoa(self):
        servico = self.abrir_manutencao()
        self.cliente.post(f"/colaborador/orcamento/{servico}", data={
            "valor_servico": "120", "status_servico": "Aguardando Aprovação", "detalhes_dano": "x"})
        with self.cliente.session_transaction() as sessao:
            sessao["user_code"] = 999
        resposta = self.cliente.post(f"/cliente/orcamento/{servico}/Aprovado", data={"pagamento": "retirada"}, follow_redirects=True)
        self.assertEqual(self.sql("SELECT status_servico FROM servicos;")[0][0], "Aguardando Aprovação")
        self.assertNotIn("aprovado com sucesso", self.texto(resposta))

    def test_venda_ja_entra_no_caixa_e_nao_fica_pendente(self):
        self.cliente.post(f"/carrinho/adicionar/{self.id_ferramenta(COMPRA)}", data={"agora": "1"})
        self.assertIn(main.formatar_moeda(PRECO_COMPRA), self.texto(self.cliente.get("/colaborador/financeiro")))
        self.assertIn("Nenhum serviço pendente", self.texto(self.cliente.get("/colaborador/painel")))


class TestePagamentoDoOrcamento(TesteBase):

    def setUp(self):
        super().setUp()
        self.cliente.post("/manutencao", data={"detalhes_equipamento": "Furadeira X", "descricao": "Não liga"})
        self.servico = self.sql("SELECT id FROM servicos;")[0][0]
        self.cliente.post(f"/colaborador/orcamento/{self.servico}", data={
            "valor_servico": "250", "status_servico": "Aguardando Aprovação", "detalhes_dano": "x"})

    def situacao(self):
        return self.sql("SELECT status_servico, pagamento FROM servicos WHERE id=%s;", self.servico)[0]

    def test_aprovar_primeiro_pergunta_como_pagar(self):
        # sem escolher o pagamento nada é aprovado: o cliente é levado para a pergunta
        resposta = self.cliente.post(f"/cliente/orcamento/{self.servico}/Aprovado")
        self.assertIn(f"/cliente/orcamento/{self.servico}/pagamento", resposta.headers["Location"])
        self.assertEqual(self.situacao(), ("Aguardando Aprovação", None))
        pagina = self.texto(self.cliente.get(resposta.headers["Location"]))
        for trecho in (main.formatar_moeda(250), "Pagar agora", "Pagar na retirada"):
            self.assertIn(trecho, pagina)

    def test_pagar_na_retirada_aprova_e_nao_vai_para_o_carrinho(self):
        resposta = self.cliente.post(f"/cliente/orcamento/{self.servico}/Aprovado", data={"pagamento": "retirada"})
        self.assertIn("/perfil", resposta.headers["Location"])
        self.assertEqual(self.situacao(), ("Aprovado", "Na retirada"))
        self.assertEqual(self.carrinho(), [])
        self.assertIn("Na retirada", self.texto(self.cliente.get("/colaborador/painel")))

    def test_pagar_agora_vai_para_o_carrinho_e_finalizar_marca_como_pago(self):
        resposta = self.cliente.post(f"/cliente/orcamento/{self.servico}/Aprovado", data={"pagamento": "agora"})
        self.assertIn("/carrinho", resposta.headers["Location"])
        self.assertEqual(self.situacao(), ("Aprovado", "Online (pendente)"))
        self.assertEqual(self.carrinho(), [{"servico": self.servico}])
        pagina = self.texto(self.cliente.get("/carrinho"))
        self.assertIn(f"Manutenção #{self.servico}", pagina)
        self.assertIn(main.formatar_moeda(250), pagina)

        self.cliente.post("/carrinho/finalizar")
        self.assertEqual(self.situacao(), ("Aprovado", "Pago online"))
        self.assertEqual(self.carrinho(), [])

    def test_quem_saiu_do_carrinho_sem_pagar_consegue_pagar_depois(self):
        self.cliente.post(f"/cliente/orcamento/{self.servico}/Aprovado", data={"pagamento": "agora"})
        self.cliente.post("/carrinho/remover/0")
        self.assertIn("Pagar agora", self.texto(self.cliente.get("/perfil")))
        self.cliente.post(f"/carrinho/pagar-servico/{self.servico}")
        self.assertEqual(self.carrinho(), [{"servico": self.servico}])

    def test_ninguem_paga_nem_ve_o_orcamento_de_outra_pessoa(self):
        self.cliente.post(f"/cliente/orcamento/{self.servico}/Aprovado", data={"pagamento": "agora"})
        with self.cliente.session_transaction() as sessao:
            sessao["user_code"] = 999
        self.assertEqual(self.texto(self.cliente.get("/carrinho")).count("btn-remover\""), 0)  # some do carrinho de quem não é o dono
        self.cliente.post(f"/carrinho/pagar-servico/{self.servico}")
        self.assertEqual(self.carrinho(), [])
        self.assertIn("/perfil", self.cliente.get(f"/cliente/orcamento/{self.servico}/pagamento").headers["Location"])


class TesteCatalogoDoColaborador(TesteBase):

    def tearDown(self):
        self.sql("DELETE FROM ferramentas WHERE modelo='Serra Circular de Teste';")
        super().tearDown()

    def test_ferramenta_nova_aparece_na_loja_com_o_preco_cadastrado(self):
        tipo = self.sql("SELECT id FROM ferramenta_tipos LIMIT 1;")[0][0]
        self.cliente.post("/colaborador/ferramentas", data={
            "marca": "Marca", "modelo": "Serra Circular de Teste", "descricao": "d",
            "tipo_ferramenta": tipo, "preco": "1999.90", "tipo_oferta": "Alugar"})
        loja = self.texto(self.cliente.get("/loja"))
        self.assertIn("Serra Circular de Teste", loja)
        self.assertIn(main.formatar_moeda(1999.90) + "/dia", loja)


class TesteDevolucao(TesteBase):

    def test_aluguel_e_devolvido_e_a_unidade_volta_ao_estoque(self):
        ferramenta = self.id_ferramenta(ALUGUEL)
        self.cliente.post(f"/carrinho/adicionar/{ferramenta}", data={"agora": "1", "dias_aluguel": "2"})
        servico = self.sql("SELECT id FROM servicos;")[0][0]
        # a diária cobrada fica guardada no aluguel
        self.assertEqual(float(self.sql("SELECT valor_diario FROM alugueis;")[0][0]), DIARIA)
        self.assertIn(ALUGUEL, self.texto(self.cliente.get("/colaborador/painel")))

        self.cliente.post(f"/colaborador/devolucao/{servico}")
        self.assertEqual(self.sql("SELECT COUNT(*) FROM unidade_ferramentas WHERE status <> 'em_estoque';")[0][0], 0)
        self.assertIsNotNone(self.sql("SELECT devolvido_em FROM alugueis;")[0][0])
        self.assertIn("Nenhuma ferramenta alugada", self.texto(self.cliente.get("/colaborador/painel")))

        # devolver de novo não faz nada
        resposta = self.cliente.post(f"/colaborador/devolucao/{servico}", follow_redirects=True)
        self.assertIn("já devolvido", self.texto(resposta))


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
