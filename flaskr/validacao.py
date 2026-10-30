"""
Validações feitas no servidor. O navegador também valida (static/js/register.js),
mas isso pode ser burlado, então o servidor confere de novo antes de gravar.
"""
import re
from flask import session

def somente_numeros(texto):
    """Tira pontos, traços e barras. Garante que seja lido como texto."""
    # O str(texto) previne falhas se o HTML/JS enviar o dado como número inteiro em vez de texto
    return re.sub(r"\D", "", str(texto) if texto else "")


def cpf_valido(cpf):
    """Confere os dois dígitos verificadores do CPF."""
    cpf = somente_numeros(cpf)
    
    # Blindagem: Se o navegador "comeu" os zeros à esquerda (ex: CPF começando em 045), recoloca-os.
    if 0 < len(cpf) < 11:
        cpf = cpf.zfill(11)
        
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
    
    # Blindagem para CNPJ: Recoloca zeros à esquerda caso tenham sido removidos pelo frontend
    if 0 < len(cnpj) < 14:
        cnpj = cnpj.zfill(14)
        
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
        return False

    def calcular(base):
        pesos = list(range(len(base) - 7, 1, -1)) + list(range(9, 1, -1))
        resto = sum(int(numero) * peso for numero, peso in zip(base, pesos)) % 11
        return 0 if resto < 2 else 11 - resto

    d1 = calcular(cnpj[:12])
    d2 = calcular(cnpj[:12] + str(d1))
    return d1 == int(cnpj[12]) and d2 == int(cnpj[13])


def pode_ver_painel():
    """
    Verifica se o utilizador atual tem perfil de Administrador ou Colaborador.
    Lê diretamente da sessão configurada no momento do Login (muito mais rápido e sem erros).
    """
    return session.get('pode_ver_painel', False)


def pode_ver_gerenciador():
    """
    Verifica se o utilizador atual tem permissão para aceder ao Gerenciador.
    """
    return session.get('pode_ver_gerenciador', False)