from .db import db_execute

def auth(user, password):
    """
    Função para fazer a autenticação do usuário
    :param user: Usuario
    :param password: Senha
    :return: True, se autenticação estiver certo. False se autenticação estiver errado.
    """
    if user == "" or password == "":
        return False

    arg = f"select count(*) from usuarios where nome_usuario=%s and senha=%s and ativo='1';"
    res = db_execute(arg, user, password, fetch_type="one")
    if not res[0]:
        print(res[1])
        return False
    return True if (res[1][0] > 0) else False

def user_create(username, password, person_id, access_type, active=True):
    """
    Função para criação de um novo usuário
    :param username: Nome de usuário
    :param password: Senha
    :param person_id: Id da pessoa cadastrada
    :param access_type: Id do tipo de acesso (perfil)
    :param active: Se conta de usuário está ativo. Padrão como True
    :return: True se conta foi criado. False se ocorreu um erro no meio do processo.
    """
    if username == "" or password == "" or person_id == "" or access_type == "" or active == "":
        return False

    # Teste
    person_id   = int(person_id)
    access_type = int(access_type)
    active      = bool(active)

    arg = "INSERT INTO usuarios (nome_usuario, senha, id_pessoa, id_perfil, ativo) VALUES (%s, %s, %s, %s, %s)"
    res = db_execute(arg, username, password, person_id, access_type, active, fetch_type="all")

    if not res[0]:
        print(res[1])
        return False
    return True

def user_update(current_username, username="", password="", id_perfil="", active=True):
    """
    Função para atualização dos dados de usuário
    :param current_username: nome do usuário em que os dados serão atualizados
    :param username: nome de usuário. Padrão como "".
    :param password: Senha. Padrão como "".
    :param id_perfil: Id do perfil. Padrão como "".
    :param active: Se conta está ativo. Padrão como True.
    :return: True, se dados foram atualizados. False se ocorreu um erro no meio do processo.
    """
    if (current_username is None) or (current_username == ""):
        return False

    user_infos = user_get(current_username)
    if user_infos is None:
        return False

    if username == "":
        username    = user_infos["username"]
    if password == "":
        password    = user_infos["password"]
    if id_perfil == "":
        id_perfil   = user_infos["id_perfil"]

    print(user_infos)

    arg = "UPDATE usuarios SET nome_usuario=%s, senha=%s, id_perfil=%s, ativo=%s WHERE nome_usuario=%s;"
    res = db_execute(arg, username, password, id_perfil, active, current_username, fetch_type="all")
    if not res[0]:
        print(res[1])
        return False
    return True

def user_get(username):
    """
    Função para extrair dados do usuário
    :param username: Nome do usuário
    :return: None se ocorrer um erro no meio do processo. Um hash table contendo os dados do usuário.
    """
    if username == "":
        return None

    arg = "SELECT * FROM usuarios WHERE nome_usuario=%s"
    res = db_execute(arg, username, fetch_type="one")
    if not res[0]:
        print(res[1])
        return None

    if res[1] is None:
        return None

    return {
        "id":           res[1][0],
        "username":     res[1][1],
        "password":     res[1][2],
        "id_person":    res[1][3],
        "id_perfil":    res[1][4],
        "active":       res[1][5],
        "created_at":   res[1][6],
        "updated_at":   res[1][7]
    }

def person_create(name, type, code, address, email, phone_number):
    """
    Função para um novo cadastro
    :param name: Nome Completo
    :param type: Tipo do usuário (pf ou pj)
    :param code: Código (CPF ou CNPJ)
    :param address: Endereço
    :param email: Email
    :param phone_number: Número de telefône
    :return: True, se a pessoa foi cadastrada no sistema. False, se ocorreu um erro no meio do processo.
    """
    if name == "" or type == "" or code == "" or address == "" or email == "" or phone_number == "":
        return False

    arg = "INSERT INTO pessoas (nome, tipo, codigo, endereco, email, telefone) VALUES (%s, %s, %s, %s, %s, %s);"
    res = db_execute(arg, name, type, code, address, email, phone_number, fetch_type="all")
    if not res[0]:
        print(res[1])
        return False
    return True

def person_update(id, name="", type="", code="", address="", email="", phone_number=""):
    """
    Função para atualizar os dados de cadastro da pessoa
    :param id: Id do usuário.
    :param name: Nome Completo. Padrão como ""
    :param type: Tipo do usuário (pf ou pj). Padrão como ""
    :param code: Código (CPF ou CNPJ). Padrão como ""
    :param address: Endereço. Padrão como ""
    :param email: Email. Padrão como ""
    :param phone_number: Número de telefône. Padrão como ""
    :return: True, se dados de cadastro foram atualizados. False, se ocorreu um erro no meio do processo.
    """
    if (id is None) or (id == ""):
        return False

    person_infos = person_get(id, by="id")
    if person_infos is None:
        return False

    if name == "":
        name = person_infos["name"]
    if type == "":
        type = person_infos["type"]
    if code == "":
        code = person_infos["code"]
    if address == "":
        address = person_infos["address"]
    if email == "":
        email = person_infos["email"]
    if phone_number == "":
        phone_number = person_infos["phone_number"]

    arg = "UPDATE pessoas SET nome=%s, tipo=%s, codigo=%s, endereco=%s, email=%s, telefone=%s WHERE id=%s;"
    res = db_execute(arg, name, type, code, address, email, phone_number, id, fetch_type="all")
    if not res[0]:
        print(res[1])
        return False
    return True

def person_get(code, by="code"):
    """
    Função para extrair dados de cadastro
    :param code: Código que será usado para filtro.
    :param by: Parâmetro para filtrar cadasstro na busca. code="code" para filtrar por (CNPJ/CPF), code="id" ou qualquer outra coisa para filtrar por id. Padrão como "code".
    :return: None, se ocorrer um erro no meio do processo. Hash table contendo os dados de cadastro.
    """
    if code == "":
        return None

    if by == "code":
        arg = "SELECT * FROM pessoas WHERE codigo=%s"
    else:
        arg = "SELECT * FROM pessoas WHERE id=%s"
    res = db_execute(arg, code, fetch_type="one")
    if not res[0]:
        print(res[1])
        return None

    if res[1] is None:
        return None

    return {
        "id":           res[1][0],
        "name":         res[1][1],
        "type":         res[1][2],
        "code":         res[1][3],
        "address":      res[1][4],
        "email":        res[1][5],
        "phone_number": res[1][6],
        "created_at":   res[1][7],
        "updated_at":   res[1][8]
    }

def person_exist(code, by="code"):
    """
    Função para checar se cadastro existe ou não no banco
    :param code: Código que será usado para filtro.
    :param by: Parâmetro para filtrar cadasstro na busca. code="code" para filtrar por (CNPJ/CPF), code="id" ou qualquer outra coisa para filtrar por id. Padrão como "code".
    :return: None, se ocorreu um erro no meio do processo. True, se cadastro já existe. False, se cadastro não existir.
    """
    if code == "":
        return None

    if by == "code":
        arg = "SELECT COUNT(*) FROM pessoas WHERE codigo=%s"
    else:
        arg = "SELECT COUNT(*) FROM pessoas WHERE id=%s"
    res = db_execute(arg, code, fetch_type="one")
    if not res[0]:
        print(res[1])
        return None

    return True if (res[1][0] > 0) else False