"""Testes unitários: cada função é testada sozinha, sem banco de dados."""
import unittest
from datetime import date
from unittest.mock import patch

import main
from model.painel import PainelModel
from model.toolmodel import ToolModel, CATALOGO_EXEMPLOS, OFERTA_PADRAO
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

    def test_ferramenta_do_catalogo_usa_o_preco_dela(self):
        modelo = "Furadeira de Impacto 750W"
        item = ToolModel.montar_item(7, "JB Pro", modelo, "descrição")
        self.assertEqual(item["id"], 7)
        self.assertEqual(item["nome"], "JB Pro " + modelo)
        self.assertEqual(item["preco"], CATALOGO_EXEMPLOS[modelo]["preco"])
        self.assertEqual(item["tipo"], "Alugar")

    def test_ferramenta_fora_do_catalogo_usa_o_padrao(self):
        item = ToolModel.montar_item(1, "Marca", "Modelo que não existe")
        self.assertEqual(item["preco"], OFERTA_PADRAO["preco"])
        self.assertEqual(item["tipo"], OFERTA_PADRAO["tipo"])


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
