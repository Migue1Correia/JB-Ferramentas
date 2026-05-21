from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "<h1>Projeto Integrador JB Ferramentas</h1>"

if __name__ == "__main__":
    app.run(debug=True)
from flask import Flask, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

# Altere com os seus dados reais do MySQL:
app.config['MYSQL_HOST']        = '' # Geralmente é localhost
app.config['MYSQL_USER']        = '' # Seu nome de usuário no banco
app.config['MYSQL_PASSWORD']    = '' # Ou deixa vazio se não tiver configurado senha
app.config['MYSQL_DB']          = '' # Nome do banco

mysql = MySQL(app)

@app.route('/')
def testar_conexao():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT VERSION();")
        versao = cursor.fetchone()
        cursor.close()
        return jsonify({
            "status": "Conectado com sucesso!",
            "versao_mysql": versao[0]
        })
    except Exception as e:
        return jsonify({
            "status": "Erro ao conectar",
            "erro": str(e)
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
