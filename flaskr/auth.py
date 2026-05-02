from db import db_execute

def auth(user, password):
    if user == "" or password == "":
        return False

    arg = f"select count(*) from usuarios where nome_usuario=%s and senha=%s"
    res = db_execute(arg, user, password, fetch_type="one")
    if not res[0]:
        print(res[1])
        return False
    return True if (res[1][0] > 0) else False

def user_create(username, password, person_id, access_type, active=True):
    if username == "" or password == "" or person_id == "" or access_type == "" or active == "":
        return False

    person_id   = int(person_id)
    access_type = int(access_type)
    active      = bool(active)

    # PS: Gerar e armazenar apenas o HASH da senha depois

    arg = "INSERT INTO usuarios (nome_usuario, senha, id_pessoa, id_perfil, ativo) VALUES (%s, %s, %s, %s, %s)"
    res = db_execute(arg, username, password, person_id, access_type, active, fetch_type="all")

    if not res[0]:
        print(res[1])
        return False
    return True




def person_create(name, type, code, address, email, phone_number):
    if name == "" or type == "" or code == "" or address == "" or email == "" or phone_number == "":
        return False

    arg = "INSERT INTO pessoas (nome, tipo, codigo, endereco, email, telefone) VALUES (%s, %s, %s, %s, %s, %s);"
    res = db_execute(arg, name, type, code, address, email, phone_number, fetch_type="all")
    if not res[0]:
        print(res[1])
        return False
    return True

def person_get(code):
    if code == "":
        return None

    arg = "SELECT * FROM pessoas WHERE codigo=%s"
    res = db_execute(arg, code, fetch_type="one")
    if not res[0]:
        print(res[1])
        return None
    return res[1]