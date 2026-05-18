from flask import Flask, render_template, request, redirect, url_for, session, flash, g
from flask_bcrypt import Bcrypt

from model.db import jb_solucoes_db, jb_bcrypt
from model.user_account import UserAccountModel
from model.person import PersonModel

app = Flask(__name__)

# Configurações do Banco de Dados
app.config['MYSQL_HOST']        = 'localhost'
app.config['MYSQL_USER']        = 'root'
app.config['MYSQL_PASSWORD']    = '@lexandre2026*'
app.config['MYSQL_DB']          = 'jb_ferramentas'

# Chave secreta obrigatória para o funcionamento de sessões e mensagens flash
app.config['SECRET_KEY']        = 'jb_ferramentas_2026'

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)

# === 1. TELA INICIAL (LANDING PAGE) ===
@app.route("/")
def main_page():
    return render_template('landing.html')


# === 2. TELA DE TRANSIÇÃO / DESTAQUES DE SERVIÇOS 
@app.route("/ferramentas")
def ferramentas_page():
    cursor = jb_solucoes_db.connection.cursor()
    
    # 1. Mantém o seu SELECT * original das ferramentas para a vitrine
    cursor.execute("SELECT * FROM ferramentas LIMIT 3")
    colunas = [col[0] for col in cursor.description]
    ferramentas = [dict(zip(colunas, row)) for row in cursor.fetchall()]
    cursor.close()
    
    # 2. Resgata o nome de usuário salvo na sessão durante o login
    usuario_logado = session.get("user_name")

    # Passa os dados recuperados para o template
      
    lista_ferramentas = [
        {"id": 1, "nome": "Furadeira", "preco": "250,00", "tipo": "Comprar"},
        {"id": 2, "nome": "Martelete", "preco": "80,00", "tipo": "Alugar"},
        {"id": 3, "nome": "Serra Tico-Tico", "preco": "150,00", "tipo": "Comprar"}
    ]
    return render_template('ferramentas.html', ferramentas=lista_ferramentas, usuario_logado=usuario_logado)
    
# === 3. CATÁLOGO COMPLETO DA LOJA ===
@app.route('/loja')
def loja_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cursor = jb_solucoes_db.connection.cursor()
    # Puxa dinamicamente todos os campos que existem na tabela ferramentas
    cursor.execute("SELECT * FROM ferramentas")
    colunas = [col[0] for col in cursor.description]
    lista_completa = [dict(zip(colunas, row)) for row in cursor.fetchall()]
    cursor.close()
    
    lista_ferramentas = [
        {"id": 1, "nome": "Furadeira", "preco": "250,00", "tipo": "Comprar"},
        {"id": 2, "nome": "Martelete", "preco": "80,00", "tipo": "Alugar"},
        {"id": 3, "nome": "Serra Tico-Tico", "preco": "150,00", "tipo": "Comprar"}
    ]
    return render_template('loja.html', ferramentas=lista_ferramentas)


# === 4. DETALHES DO PRODUTO SELECIONADO ===
@app.route('/detalhe/<int:id>')
def detalhe_produto(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    cursor = jb_solucoes_db.connection.cursor()
    # Usamos SELECT * para trazer todas as colunas dinamicamente sem quebrar por nomes
    cursor.execute("SELECT * FROM ferramentas WHERE id = %s", (id,))
    row = cursor.fetchone()
    
    if row:
        colunas = [col[0] for col in cursor.description]
        ferramenta_selecionada = dict(zip(colunas, row))
    else:
        ferramenta_selecionada = None
        
    cursor.close()
    return render_template('detalhes.html', ferramenta=ferramenta_selecionada)


# === 5. PROCESSAMENTO DE LOGIN ===
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")
        
        # 1. Utiliza a função estática auth do seu model para validar usuário e senha
        if UserAccountModel.auth(usuario, senha):
            
            # 2. Se a senha estiver correta, puxamos o dicionário de dados da conta
            dados_conta = UserAccountModel.get(usuario)
            
            # 3. Pegamos a chave 'id_person' tratada de forma segura diretamente do seu model
            if dados_conta and "id_person" in dados_conta:
                session['user_code'] = dados_conta["id_person"]
                session['logged_in'] = True
                
                # Salva o nome digitado no formulário para usá-lo na saudação do painel
                session['user_name'] = usuario 
                
                flash("Login realizado com sucesso! Bem-vindo de volta.", "success")
                return redirect(url_for('ferramentas_page'))
        
        # Se falhar o login, retorna o erro no formulário
        return render_template('index.html', status="Usuário ou senha incorretos.")
            
    return render_template('index.html')


# === 6. TELA DE PERFIL DO USUÁRIO ===
@app.route('/perfil', methods=['GET', 'POST'])
def perfil_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_code = session.get('user_code')
    status = None
    
    if request.method == "POST":
        status = "Dados updated com sucesso!"

    # Busca os dados cadastrais usando uma consulta direta e segura na tabela de pessoas
    try:
        cursor = jb_solucoes_db.connection.cursor()
        # Seleciona as colunas comuns que existem em tabelas de pessoas físicas/jurídicas
        cursor.execute("SELECT * FROM pessoas WHERE id = %s", (user_code,))
        colunas = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        cursor.close()
        
        user_infos = dict(zip(colunas, row)) if row else None
    except Exception:
        # Fallback caso sua tabela não se chame 'pessoas'
        user_infos = PersonModel.get(user_code)
    
    if user_infos is None:
        flash("Erro ao carregar os dados do perfil.", "danger")
        return redirect(url_for('loja_page'))

    return render_template('perfil.html', user_infos=user_infos, status=status)


# === 7. CADASTRO / REGISTRO DE NOVOS USUÁRIOS COMPLETO ===
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


# === 8. LOGOUT ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main_page'))


# === 9. ROTA DE MANUTENÇÃO ===
@app.route('/manutencao')
def manutencao_page(): 
    return render_template('manutencao.html')


if __name__ == "__main__":
    app.run(debug=True)