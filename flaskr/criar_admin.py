"""
Cria o administrador do sistema (ou promove um usuário que já existe).

Como usar (com a .venv ativada):
    cd flaskr
    python criar_admin.py

O script pergunta o usuário e a senha. A senha não aparece na tela e não fica guardada
em nenhum arquivo: no banco entra só a versão embaralhada (bcrypt).
"""
from getpass import getpass

from main import app, jb_bcrypt, PERFIL_ADMINISTRADOR, PERFIL_CLIENTE, PERFIS_COLABORADOR
from model.db import db_execute
from model.person import PersonModel
from model.user_account import UserAccountModel


def criar_admin(usuario, senha):
    """Devolve a mensagem do que foi feito. Levanta ValueError se usuário ou senha não servirem."""
    if not usuario:
        raise ValueError("Informe o nome de usuário.")
    if len(senha) < 8:
        raise ValueError("A senha precisa ter pelo menos 8 caracteres.")

    # Garante que os perfis do sistema existem
    for perfil in PERFIS_COLABORADOR + (PERFIL_CLIENTE,):
        UserAccountModel.id_do_perfil(perfil)
    id_admin = UserAccountModel.id_do_perfil(PERFIL_ADMINISTRADOR)
    senha_embaralhada = jb_bcrypt.generate_password_hash(senha).decode("utf-8")

    conta = UserAccountModel.get(usuario)
    if conta:
        res = db_execute("UPDATE usuarios SET senha=%s, id_perfil=%s, ativo=1 WHERE id=%s;",
                         senha_embaralhada, id_admin, conta["id"])
        if not res[0]:
            raise ValueError(f"Erro no banco: {res[1]}")
        return f"O usuário {conta['username']} já existia: agora é Administrador, com a senha nova."

    # Toda conta precisa de uma pessoa
    res = db_execute(
        "INSERT INTO pessoas (nome, tipo, endereco, email, telefone) VALUES (%s, 'pj', 'JB Ferramentas', %s, '0000000000');",
        "Administrador", f"{usuario}@jbferramentas.local")
    if not res[0]:
        raise ValueError(f"Erro no banco: {res[1]}")
    if not UserAccountModel.create(usuario, senha_embaralhada, res[1], id_admin, True):
        PersonModel.delete(res[1])  # não deixa pessoa sem conta
        raise ValueError("Erro ao criar a conta no banco.")
    return f"Administrador {usuario} criado."


if __name__ == "__main__":
    usuario = input("Usuário do administrador: ").strip()
    senha = getpass("Senha (mínimo 8 caracteres, não aparece enquanto digita): ")
    if senha != getpass("Repita a senha: "):
        raise SystemExit("As senhas não são iguais.")
    with app.app_context():
        try:
            print(criar_admin(usuario, senha))
        except ValueError as erro:
            raise SystemExit(str(erro))
