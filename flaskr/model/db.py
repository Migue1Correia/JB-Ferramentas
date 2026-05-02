from flask_mysqldb import MySQL

jb_solucoes_db = MySQL()

def db_execute(arg, *parsing, fetch_type="all"):

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