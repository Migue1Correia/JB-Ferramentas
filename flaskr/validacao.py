"""
Validações feitas no servidor. O navegador também valida (static/js/register.js),
mas isso pode ser burlado, então o servidor confere de novo antes de gravar.
"""
import re


def somente_numeros(texto):
    """Tira pontos, traços e barras. Ex.: '123.456.789-09' -> '12345678909'"""
    return re.sub(r"\D", "", texto or "")


def cpf_valido(cpf):
    """Confere os dois dígitos verificadores do CPF."""
    cpf = somente_numeros(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False

    for posicao in (9, 10):
        soma = sum(int(cpf[i]) * (posicao + 1 - i) for i in range(posicao))
        digito = (soma * 10) % 11 % 10
        if digito != int(cpf[posicao]):
            return False
    return True


def cnpj_valido(cnpj):
    """Confere os dois dígitos verificadores do CNPJ."""
    cnpj = somente_numeros(cnpj)
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def calcular(base):
        pesos = list(range(len(base) - 7, 1, -1)) + list(range(9, 1, -1))
        resto = sum(int(numero) * peso for numero, peso in zip(base, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    d1 = calcular(cnpj[:12])
    d2 = calcular(cnpj[:12] + str(d1))
    return d1 == int(cnpj[12]) and d2 == int(cnpj[13])
