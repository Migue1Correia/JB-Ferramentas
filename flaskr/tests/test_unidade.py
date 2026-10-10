"""Testes unitários: cada função é testada sozinha, sem banco de dados."""
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

import main
from model.painel import PainelModel
from model.toolmodel import ToolModel, IMAGEM_PADRAO
from validacao import somente_numeros, cpf_valido, cnpj_valido


class TesteValidacao(unittest.TestCase):

    def test_somente_numeros(self):
        self.assertEqual(somente_numeros("529.982.247-25"), "52998224725")
        self.assertEqual(somente_numeros(None), "")

    def test_cpf_valido(self):
        self.assertTrue(cpf_valido("529.982.247-25"))
        self.assertTrue(cpf_valido("52998224725"))

    def test_cpf_invalido(self):
        self.assertFalse(cpf_valido("529.982.247-26"))  # último dígito errado
        self.assertFalse(cpf_valido("111.111.111-11"))  # todos os dígitos iguais
        self.assertFalse(cpf_valido("123"))             # curto demais
        self.assertFalse(cpf_valido(""))

    def test_cnpj_valido(self):
        self.assertTrue(cnpj_valido("11.222.333/0001-81"))
        self.assertTrue(cnpj_valido("11444777000161"))

    def test_cnpj_invalido(self):
        self.assertFalse(cnpj_valido("11.222.333/0001-82"))  # último dígito errado
        self.assertFalse(cnpj_valido("00.000.000/0000-00"))  # todos os dígitos iguais
        self.assertFalse(cnpj_valido("529.982.247-25"))      # é um CPF


class TesteMoeda(unittest.TestCase):

    def test_formato_brasileiro(self):
        self.assertEqual(main.formatar_moeda(1234.5), "R$ 1.234,50")
        self.assertEqual(main.formatar_moeda(35), "R$ 35,00")
        self.assertEqual(main.formatar_moeda(1000000), "R$ 1.000.000,00")

    def test_valor_vazio_vira_zero(self):
        self.assertEqual(main.formatar_moeda(None), "R$ 0,00")


class TesteCatalogo(unittest.TestCase):

    def test_linha_do_banco_vira_item_da_loja(self):
        item = ToolModel.montar_item((7, "JB Pro", "Furadeira X", "descrição", Decimal("35.00"), "Alugar", "img/x.png"))
        self.assertEqual(item["id"], 7)
        self.assertEqual(item["nome"], "JB Pro Furadeira X")
        self.assertEqual(item["preco"], 35.0)
        self.assertEqual(item["tipo"], "Alugar")
        self.assertEqual(item["imagem"], "img/x.png")

    def test_ferramenta_sem_foto_usa_a_imagem_padrao(self):
        item = ToolModel.montar_item((1, "Marca", "Modelo", None, Decimal("10"), "Comprar", None))
        self.assertEqual(item["imagem"], IMAGEM_PADRAO)

    def test_cadastro_recusa_preco_ou_oferta_invalidos(self):
        # Nenhum destes chega ao banco: a validação barra antes
        self.assertEqual(ToolModel.create("M", "X", "", 1, "abc", "Comprar")[0], False)
        self.assertEqual(ToolModel.create("M", "X", "", 1, "-5", "Comprar")[0], False)
        self.assertEqual(ToolModel.create("M", "X", "", 1, "10", "Trocar")[0], False)


class TesteCriarAdmin(unittest.TestCase):

    def test_recusa_usuario_vazio_e_senha_curta(self):
        # A validação barra antes de chegar ao banco
        from criar_admin import criar_admin
        with self.assertRaises(ValueError):
            criar_admin("", "senha-grande-o-bastante")
        with self.assertRaises(ValueError):
            criar_admin("chefe", "1234567")


class TestePainel(unittest.TestCase):
    """O banco é trocado por uma resposta falsa (mock), para testar só a conta."""

    def test_soma_por_tipo_e_preenche_meses_vazios(self):
        hoje = date.today()
        linhas = (
            (hoje.year, hoje.month, "venda", 300.50, 2),
            (hoje.year, hoje.month, "aluguel", 105, 1),
        )
        with patch("model.painel.db_execute", return_value=(True, linhas)):
            dados = PainelModel.get_resumo_mensal()

        self.assertFalse(dados["erro"])
        self.assertEqual(len(dados["rotulos"]), 12)
        self.assertEqual(dados["faturamento_total"], 405.50)
        self.assertEqual(dados["total_servicos"], 3)

        vendas, alugueis, manutencoes = dados["series"]
        self.assertEqual(vendas["valores"], [0.0] * 11 + [300.50])   # só o mês atual tem venda
        self.assertEqual(vendas["quantidades"], [0] * 11 + [2])
        self.assertEqual(alugueis["total_valor"], 105)
        self.assertEqual(manutencoes["total_quantidade"], 0)

    def test_banco_vazio(self):
        with patch("model.painel.db_execute", return_value=(True, ())):
            dados = PainelModel.get_resumo_mensal()
        self.assertEqual(dados["total_servicos"], 0)
        self.assertEqual(dados["faturamento_total"], 0)

    def test_erro_no_banco_e_avisado(self):
        with patch("model.painel.db_execute", return_value=(False, "erro")):
            dados = PainelModel.get_resumo_mensal()
        self.assertTrue(dados["erro"])


if __name__ == "__main__":
    unittest.main()
