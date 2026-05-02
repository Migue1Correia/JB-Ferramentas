from flask import Flask, render_template, request
from flask_bcrypt import Bcrypt

from model.db import jb_solucoes_db, jb_bcrypt

from model.user_account import UserAccountModel
from model.person import PersonModel


app = Flask(__name__)

app.config['MYSQL_HOST']        = 'Seu host' #Geralmente é localhost
app.config['MYSQL_USER']        = 'Seu usuário para acessar o MySQL'
app.config['MYSQL_PASSWORD']    = 'Sua senha para acessar o MySQL' # Ou deixa vazio se não tiver configurado senha
app.config['MYSQL_DB']          = 'O nome do seu banco'

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)

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

        if not UserAccountModel.auth(request.form['usuario'], request.form['senha']):
            status = "Erro ao autenticar usuário."
        UserAccountModel.update("alex", "Alex123")
        return render_template('auth.html', status=status)

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template('register.html')

    elif request.method == "POST":
        status = "Cadastro realizado com sucesso"
        name            = request.form['nome']
        type            = request.form['tipo']
        code            = request.form['codigo']
        address         = request.form['endereco']
        email           = request.form['email']
        phone_number    = request.form['telefone']

        user            = request.form['usuario']
        password        = request.form['senha']

        if PersonModel.exist(code, by="code"):
            status = "Já tem uma pessoa cadastrado com esse código de CPF/CNPJ. For favor, faça o login."
            return render_template('register.html', status=status)

        if not PersonModel.create(name, type, code, address, email, phone_number):
            status = "Não foi possível fazer o cadastro"
            return render_template('register.html', status=status)

        person_infos = PersonModel.get(code)

        if person_infos is None:
            status = "Não foi possível extrair o código da pessoa"
            return render_template('register.html', status=status)

        hashed_password = jb_bcrypt.generate_password_hash(password).decode("utf-8")

        if not UserAccountModel.create(user, hashed_password, person_infos["id"], 1, True):
            status = f"Não foi possível gerar uma conta usuário para o {person_infos[1]}. Por favor, tente novamente!"

        return render_template('register.html', status=status)
