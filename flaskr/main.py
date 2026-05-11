from flask import Flask, render_template, request
from flask_bcrypt import Bcrypt

from model.db import jb_solucoes_db, jb_bcrypt

from model.user_account import UserAccountModel
from model.person import PersonModel


app = Flask(__name__)

app.config['MYSQL_HOST']        = 'localhost' #Geralmente é localhost
app.config['MYSQL_USER']        = 'root'
app.config['MYSQL_PASSWORD']    = '@lexandre2026*' # Ou deixa vazio se não tiver configurado senha
app.config['MYSQL_DB']          = 'jb_ferramentas'

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)

# Depois configurar um arquivo .env para armazenar os dados de acesso ao banco


@app.route("/")
def main_page():
    return render_template('index.html')
ferramentas = [
        {'id': 1, 'nome': 'Furadeira', 'preco': '450,00', 'tipo': 'Comprar'},
        {'id': 2, 'nome': 'Martelete', 'preco': '80,00', 'tipo': 'Alugar'}
    ]
    

@app.route("/ferramentas")
def ferramentas():
    
    lista_ferramentas = [
        {"id": 1, "nome": "Furadeira", "preco": "250,00", "tipo": "Comprar"},
        {"id": 2, "nome": "Martelete", "preco": "80,00", "tipo": "Alugar"},
        {"id": 3, "nome": "Serra Tico-Tico", "preco": "150,00", "tipo": "Comprar"}
    ]
    return render_template('ferramentas.html', ferramentas=lista_ferramentas)


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

    if request.method == "POST":
        name = request.form.get('nome')
        user_type = request.form.get('tipo')
        code = request.form.get('code')
        address = request.form.get('endereco')
        email = request.form.get('email')
        phone_number = request.form.get('telefone')
        user = request.form.get('usuario')
        password = request.form.get('senha')

        if PersonModel.exist(code, by="code"):
            status = "Já tem uma pessoa cadastrada com esse código de CPF/CNPJ. Por favor, faça o login."
            return render_template('register.html', status=status)

        if not PersonModel.create(name, user_type, code, address, email, phone_number):
            status = "Não foi possível fazer o cadastro"
            return render_template('register.html', status=status)

        person_infos = PersonModel.get(code)

        if person_infos is None:
            status = "Não foi possível extrair o código da pessoa"
            return render_template('register.html', status=status)

        hashed_password = jb_bcrypt.generate_password_hash(password).decode("utf-8")

        if not UserAccountModel.create(user, hashed_password, person_infos["id"], 1, True):
            status = f"Não foi possível gerar uma conta usuário para o {person_infos.get('nome', user)}. Por favor, tente novamente!"
            return render_template('register.html', status=status)

        status = "Cadastro realizado com sucesso"
        return render_template('register.html', status=status)
    
@app.route('/manutencao')
def manutencao_page(): 
    return render_template('manutencao.html')

@app.route('/loja')
def loja_page():
    # Esta lista simula os dados que virão do seu banco de dados
    lista_ferramentas = [
        {"id": 1, "nome": "Furadeira Bosch", "preco": "450,00", "tipo": "Comprar"},
        {"id": 2, "nome": "Martelete Makita", "preco": "80,00", "tipo": "Alugar"},
        {"id": 3, "nome": "Serra Circular", "preco": "320,00", "tipo": "Comprar"},
        {"id": 4, "nome": "Andaime", "preco": "50,00", "tipo": "Alugar"}
    ]
    return render_template('loja.html', ferramentas=lista_ferramentas)

@app.route('/detalhe/<int:id>')
def detalhe_produto(id):
    # Repetimos a lista para simular o banco de dados
    lista_ferramentas = [
        {"id": 1, "nome": "Furadeira", "preco": "250,00", "tipo": "Comprar"},
        {"id": 2, "nome": "Martelete", "preco": "80,00", "tipo": "Alugar"},
        {"id": 3, "nome": "Serra Tico-Tico", "preco": "150,00", "tipo": "Comprar"}
    ]
    
    # Busca a ferramenta correta pelo ID
    ferramenta_selecionada = next((item for item in lista_ferramentas if item["id"] == id), None)
    
    if not ferramenta_selecionada:
        return "Ferramenta não encontrada", 404

    return render_template('detalhes.html', ferramenta=ferramenta_selecionada)