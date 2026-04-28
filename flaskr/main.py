from flask import Flask, render_template, request
from db import jb_solucoes_db, db_execute
from auth import auth

app = Flask(__name__)

app.config['MYSQL_HOST']        = 'Seu host' #Geralmente é localhost
app.config['MYSQL_USER']        = 'Seu usuário para acessar o MySQL'
app.config['MYSQL_PASSWORD']    = 'Sua senha para acessar o MySQL' # Ou deixa vazio se não tiver configurado senha
app.config['MYSQL_DB']          = 'O nome do seu banco'
jb_solucoes_db.init_app(app)

# Depois configurar um arquivo .env para armazenar os dados de acesso ao banco

@app.route("/")
def main_page():
    return render_template('index.html')

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "GET":
        return render_template('auth.html')

    elif request.method == "POST":
        status = "Usuário autenticado"
        if not auth(request.form['usuario'], request.form['senha']):
            status = "Erro ao autenticar usuário."
        return render_template('auth.html', status=status)
