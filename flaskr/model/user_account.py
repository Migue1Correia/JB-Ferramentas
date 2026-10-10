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
        if not user or not password:
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
    def listar():
        """
        Função para listar todos os usuários com o perfil de cada um
        :return: Lista de dicionários (id, usuario, nome, id_perfil). Lista vazia se ocorrer um erro.
        """
        arg = """
            SELECT u.id, u.nome_usuario, p.nome, u.id_perfil
            FROM usuarios u JOIN pessoas p ON p.id = u.id_pessoa
            ORDER BY u.nome_usuario;
        """
        res = db_execute(arg, fetch_type="all")
        if not res[0]:
            print(res[1])
            return []
        return [{"id": linha[0], "usuario": linha[1], "nome": linha[2], "id_perfil": linha[3]} for linha in res[1]]

    @staticmethod
    def mudar_perfil(id_usuario, id_perfil):
        """
        Função para trocar o perfil de um usuário
        :param id_usuario: Id do usuário
        :param id_perfil: Id do novo perfil
        :return: True, se o perfil foi trocado. False, se ocorreu um erro (ex.: perfil que não existe).
        """
        res = db_execute("UPDATE usuarios SET id_perfil=%s WHERE id=%s;", id_perfil, id_usuario)
        if not res[0]:
            print(res[1])
            return False
        return True

    @staticmethod
    def get_perfil(username):
        """
        Função para saber o perfil de um usuário
        :param username: Nome do usuário
        :return: O nome do perfil (ex.: "Cliente", "Administrador"). None se não encontrar.
        """
        arg = "SELECT p.perfil FROM usuarios u JOIN perfis p ON p.id = u.id_perfil WHERE u.nome_usuario=%s"
        res = db_execute(arg, username, fetch_type="one")
        if not res[0] or res[1] is None:
            return None
        return res[1][0]

    @staticmethod
    def id_do_perfil(perfil):
        """
        Função para achar o id de um perfil pelo nome. Se o perfil ainda não existir, ele é criado.
        :param perfil: Nome do perfil (ex.: "Cliente")
        :return: O id do perfil. None se ocorrer um erro no meio do processo.
        """
        res = db_execute("SELECT id FROM perfis WHERE perfil=%s", perfil, fetch_type="one")
        if not res[0]:
            print(res[1])
            return None
        if res[1]:
            return res[1][0]

        res = db_execute("INSERT INTO perfis (perfil) VALUES (%s)", perfil)
        return res[1] if res[0] else None

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
