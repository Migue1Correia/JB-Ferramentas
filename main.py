from flask import Flask, render_template, request
from flask_bcrypt import Bcrypt

from model.db import jb_solucoes_db, jb_bcrypt

from model.user_account import UserAccountModel
from model.person import PersonModel
from flask import Flask, render_template, request, redirect, url_for




app = Flask(__name__)


# Configurações do Banco de Dados JB Ferramentas
app.config['MYSQL_HOST']     = 'localhost'
app.config['MYSQL_USER']     = 'root'
app.config['MYSQL_PASSWORD'] = 'Papel@1987'
app.config['MYSQL_DB']       = 'jb_ferramentas'

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)

@app.route('/')
def main_page():
    # Agora a Landing Page é a entrada do site
    return render_template('landing.html')

@app.route('/login-page')
def login_view():
    return render_template('index.html') # ESTA LINHA PRECISA DE 4 ESPAÇOS (TAB)

@app.route('/dashboard')
def dashboard():
    nome_usuario = "Monique" 
    return render_template('dashboard.html', nome=nome_usuario)

@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        # Tenta autenticar
        if UserAccountModel.auth(request.form['usuario'], request.form['senha']):
            # SE DEU CERTO: Redireciona para a nova rota do dashboard
            return redirect(url_for('dashboard'))
        else:
            # SE DEU ERRO: Mantém na página com aviso
            return render_template('index.html', status="Erro ao autenticar usuário.")

    # Se for GET (abrir a página), mostra a tela de login normal
    return render_template('index.html')
@app.route("/register", methods=['GET', 'POST'])

def register():
    if request.method == "GET":
        return render_template('register.html')

    elif request.method == "POST":
        # Coleta de dados
        name         = request.form['nome']
        type         = request.form['tipo']
        code         = request.form['codigo']
        address      = request.form['endereco']
        email        = request.form['email']
        phone_number = request.form['telefone']
        user         = request.form['usuario']
        password     = request.form['senha']

        # 1. Verifica se o CPF/Código já existe
        if PersonModel.exist(code, by="code"): 
            # DICA: Aqui usamos 'name' (que já pegamos do form) porque person_infos ainda não existe
            status = f"Já tem uma pessoa cadastrada com esse código. Por favor, faça o login."
            return render_template('register.html', status=status)

        # 2. Cria a pessoa no banco
        if not PersonModel.create(name, type, code, address, email, phone_number):
            status = "Não foi possível fazer o cadastro"
            return render_template('register.html', status=status)

        # 3. Busca os dados da pessoa que acabou de ser criada para pegar o ID
        person_infos = PersonModel.get(code)

        if person_infos is None:
            status = "Não foi possível extrair os dados da pessoa"
            return render_template('register.html', status=status)

        # 4. Gera o hash da senha
        hashed_password = jb_bcrypt.generate_password_hash(password).decode("utf-8")

        # 5. Tenta criar a conta de usuário vinculado à pessoa
        if not UserAccountModel.create(user, hashed_password, person_infos["id"], 1, True):
            status = f"Não foi possível gerar uma conta usuário para {name}. Tente novamente!"
            return render_template('register.html', status=status)

        # --- AQUI ESTAVA O ERRO ---
        # Se o código chegou até aqui, significa que TUDO DEU CERTO!
        # Precisamos retornar o template de login (index.html) com mensagem de sucesso.
        return render_template('index.html', status="Cadastro realizado com sucesso! Faça seu login.")