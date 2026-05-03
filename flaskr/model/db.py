from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt

# Objecto que armazena todas as infos para acessar o seu banco de dados.
# Para configurar o acesso ao seu banco de dados, adicione as infos que estão em flaskr/main.py em app.config
jb_solucoes_db = MySQL()

# Importei aqui por enquanto... Talvez mudar depois
jb_bcrypt = Bcrypt()

def db_execute(arg, *parsing, fetch_type="all"):
    """
    Função para a execução de comandos MySQL
    :param arg: Argumento MySQL. Exemplo: "SELECT * FROM pessoas"
    :param parsing: Variavel/is que serão concatenados no argumento caso hajá comparação de valores.
            Exemplo, se o argumento é "SELECT * FROM pessoas WHERE id=%s", o parsing vai substituir o "%s"
            pelo valor do parsing.Lembrando que o parsing pode conter mais de um valor dependendo do argumento.
    :param fetch_type: Se fetch_type="all" ou qualquer outra coisa, então a função vai retornar todas as consultas do argumento.
            Se fetch_type="one", então irá retornar somente o primeiro registro da consulta do argumento.
    :return: Uma lista com a seguinte estrutura: [True/False, Array]: True/False: Para saber se ocorreu tudo bem com o chamado para o banco.
            Array: Contém os resultados da consulta no banco
    """

    if len(arg) == 0:
        return False, None

    try:
        c               = jb_solucoes_db.connection.cursor()
        p               = ()
        result          = None

        for parse in parsing:
            p += (parse,)

        c.execute(arg, p)
        jb_solucoes_db.connection.commit()

        if fetch_type == "one":
            result = c.fetchone()
        else:
            result = c.fetchall()

        c.close()
        return True, result
    except Exception as e:
        return False, str(e)