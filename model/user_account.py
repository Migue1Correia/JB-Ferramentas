from .db import db_execute, jb_bcrypt

class UserAccountModel:

    @staticmethod
    def auth(user, password):
        """
        Função para fazer a autenticação do usuário
        :param user: Usuario
        :param password: Senha
        :return: True, se autenticação estiver certo. False se autenticação estiver errado.
        """
        if user == "" or password == "":
            return False

        arg = f"SELECT senha FROM usuarios where nome_usuario=%s and ativo='1';"
        res = db_execute(arg, user,  fetch_type="one")
        if not res[0]:
            print(res[1])
            return False

        if res[1] is None:
            return False

        is_valid = jb_bcrypt.check_password_hash(res[1][0], password)

        return is_valid

    @staticmethod
    def create(username, password, person_id, access_type, active=True):
        """
        Função para criação de um novo usuário
        :param username: Nome de usuário
        :param password: Senha em formato de Hash
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

    @staticmethod
    def update(current_username, username="", password="", id_perfil="", active=True):
        """
        Função para atualização dos dados de usuário
        :param current_username: nome do usuário em que os dados serão atualizados
        :param username: nome de usuário. Padrão como "".
        :param password: Senha em formato de Hash. Padrão como "".
        :param id_perfil: Id do perfil. Padrão como "".
        :param active: Se conta está ativo. Padrão como True.
        :return: True, se dados foram atualizados. False se ocorreu um erro no meio do processo.
        """
        if (current_username is None) or (current_username == ""):
            return False

        user_infos = UserAccountModel.get(current_username)
        if user_infos is None:
            return False

        if username == "":
            username    = user_infos["username"]
        if password == "":
            password    = user_infos["password"]
        if id_perfil == "":
            id_perfil   = user_infos["id_perfil"]

        arg = "UPDATE usuarios SET nome_usuario=%s, senha=%s, id_perfil=%s, ativo=%s WHERE nome_usuario=%s;"
        res = db_execute(arg, username, password, id_perfil, active, current_username, fetch_type="all")
        if not res[0]:
            print(res[1])
            return False
        return True

    @staticmethod
    def get(username):
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