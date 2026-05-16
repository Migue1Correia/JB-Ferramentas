from .db import db_execute

class PersonModel:

    @staticmethod
    def create(name, person_type, codigo, address, email, phone_number):
        """
        Função para um novo cadastro
        :param name: Nome Completo
        :param person_type: Tipo do usuário (pf ou pj)
        :param code: Código (CPF ou CNPJ)
        :param address: Endereço
        :param email: Email
        :param phone_number: Número de telefône
        :return: True, se a pessoa foi cadastrada no sistema. False, se ocorreu um erro no meio do processo.
        """
        if name == "" or person_type == "" or codigo == "" or address == "" or email == "" or phone_number == "":
            return False

        arg = "INSERT INTO pessoas (nome, tipo, codigo, endereco, email, telefone) VALUES (%s, %s, %s, %s, %s, %s);"
        res = db_execute(arg, name, person_type, codigo, address, email, phone_number, fetch_type="all")
        if not res[0]:
            print(res[1])
            return False
        return True

    @staticmethod
    def update(id, name="", person_type="", code="", address="", email="", phone_number=""):
        """
        Função para atualizar os dados de cadastro da pessoa
        :param id: Id do usuário.
        :param name: Nome Completo. Padrão como ""
        :param person_type: Tipo do usuário (pf ou pj). Padrão como ""
        :param code: Código (CPF ou CNPJ). Padrão como ""
        :param address: Endereço. Padrão como ""
        :param email: Email. Padrão como ""
        :param phone_number: Número de telefône. Padrão como ""
        :return: True, se dados de cadastro foram atualizados. False, se ocorreu um erro no meio do processo.
        """
        if (id is None) or (id == ""):
            return False

        person_infos = PersonModel.get(id, by="id")
        if person_infos is None:
            return False

        if name == "":
            name = person_infos["name"]
        if person_type == "":
            person_type = person_infos["type"]
        if code == "":
            code = person_infos["code"]
        if address == "":
            address = person_infos["address"]
        if email == "":
            email = person_infos["email"]
        if phone_number == "":
            phone_number = person_infos["phone_number"]

        arg = "UPDATE pessoas SET nome=%s, tipo=%s, codigo=%s, endereco=%s, email=%s, telefone=%s WHERE id=%s;"
        res = db_execute(arg, name, person_type, code, address, email, phone_number, id, fetch_type="all")
        if not res[0]:
            print(res[1])
            return False
        return True

    @staticmethod
    def get(code, by="code"):
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
            "id": res[1][0],
            "name": res[1][1],
            "type": res[1][2],
            "code": res[1][3],
            "address": res[1][4],
            "email": res[1][5],
            "phone_number": res[1][6],
            "created_at": res[1][7],
            "updated_at": res[1][8]
        }

    @staticmethod
    def exist(codigo, by="code"):
        """
        Função para checar se cadastro existe ou não no banco
        :param code: Código que será usado para filtro.
        :param by: Parâmetro para filtrar cadasstro na busca. code="code" para filtrar por (CNPJ/CPF), code="id" ou qualquer outra coisa para filtrar por id. Padrão como "code".
        :return: None, se ocorreu um erro no meio do processo. True, se cadastro já existe. False, se cadastro não existir.
        """
        if codigo == "":
            return None

        if by == "codigo":
            arg = "SELECT COUNT(*) FROM pessoas WHERE codigo=%s"
        else:
            arg = "SELECT COUNT(*) FROM pessoas WHERE id=%s"
        res = db_execute(arg, codigo, fetch_type="one")
        if not res[0]:
            print(res[1])
            return None

        return True if (res[1][0] > 0) else False