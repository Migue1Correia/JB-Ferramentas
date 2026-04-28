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


def user_create(name, type, code, address, email, phone_number):
    if name == "" or type == "" or code == "" or address == "" or email == "" or phone_number == "":
        return False

    arg = "INSERT INTO pessoas (nome, tipo, codigo, endereco, email, telefone) VALUES (%s, %s, %s, %s, %s, %s);"
    res = db_execute(arg, name, type, code, address, email, phone_number, fetch_type="all")
    if not res[0]:
        print(res[1])
        return False
    return True

def user_get(code):
    if code == "":
        return False

    arg = "SELECT * FROM pessoas WHERE codigo=%s"
    res = db_execute(arg, code, fetch_type="all")
    print(res)
    return True
