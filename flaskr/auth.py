from db import db_execute

def auth(user, password):
    if user == "" or password == "":
        return False

    arg = f"select count(*) from usuarios where nome_usuario=%s and senha=%s and ativo='1';"
    res = db_execute(arg, user, password, fetch_type="one")
    if not res[0]:
        print(res[1])
        return False
    return True if (res[1][0] > 0) else False

def user_create(username, password, person_id, access_type, active=True):
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
    if name == "" or type == "" or code == "" or address == "" or email == "" or phone_number == "":
        return False

    arg = "INSERT INTO pessoas (nome, tipo, codigo, endereco, email, telefone) VALUES (%s, %s, %s, %s, %s, %s);"
    res = db_execute(arg, name, type, code, address, email, phone_number, fetch_type="all")
    if not res[0]:
        print(res[1])
        return False
    return True

def person_update(id, name="", type="", code="", address="", email="", phone_number=""):
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