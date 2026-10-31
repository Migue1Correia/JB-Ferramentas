import os
import secrets
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flask_wtf.csrf import CSRFProtect, CSRFError
from model.db import jb_solucoes_db, jb_bcrypt
from model.user_account import UserAccountModel
from model.person import PersonModel
from model.toolmodel import ToolModel
from model.service import ServiceModel
from model.colaborador import ColaboradorModel
from model.admin import AdminModel
from model.painel import PainelModel
from validacao import somente_numeros, cpf_valido, cnpj_valido
from dotenv import load_dotenv

# Carrega as configurações do arquivo .env
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'jb_ferramentas')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', '3306'))

chave_secreta = os.getenv('SECRET_KEY', '')
if not chave_secreta or chave_secreta.startswith('troque'):
    print("AVISO: defina SECRET_KEY no arquivo .env. Usando uma chave temporária.")
    chave_secreta = secrets.token_hex(32)
app.config['SECRET_KEY'] = chave_secreta

# Blindagem de Cookies e Sessão (Segurança)
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Impede que scripts maliciosos leiam os cookies (Proteção XSS)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax' # Previne ataques de falsificação de solicitações (CSRF)

# Proteção CSRF
csrf = CSRFProtect(app)

# Pasta de uploads global
UPLOAD_FOLDER = os.path.join(app.root_path, 'static', 'uploads', 'equipamentos')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)


@app.errorhandler(CSRFError)
def formulario_expirado(erro):
    flash("O formulário expirou. Tente enviar de novo.", "danger")
    return redirect(request.referrer or url_for('login'))


@app.context_processor
def variaveis_dos_menus():
    """Injeta as permissões corretas (definidas no login) em todos os ficheiros HTML."""
    return {
        "pode_ver_painel": session.get('pode_ver_painel', False),
        "pode_ver_gerenciador": session.get('pode_ver_gerenciador', False)
    }


@app.template_filter('moeda')
def formatar_moeda(valor):
    texto = f"{float(valor or 0):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


@app.template_filter('zap')
def formatar_zap(telefone):
    """Limpa o telefone e adiciona o código 55 do Brasil para o link do WhatsApp"""
    if not telefone:
        return ""
    numeros = ''.join(filter(str.isdigit, str(telefone)))
    return f"55{numeros}" if numeros else ""


# === 1. TELA INICIAL (LANDING PAGE) ===
@app.route("/", methods=['GET'])
def main_page():
    os_busca = request.args.get('os_busca')
    resultado_os = None
    
    if os_busca:
        # Limpa os espaços e transforma em maiúsculas
        os_busca = os_busca.strip().upper()
        
        # Se o cliente digitar apenas "24903", o sistema ajusta automaticamente para "OS-24903"
        termo_busca = f"OS-{os_busca}" if not os_busca.startswith("OS-") else os_busca
            
        try:
            cursor = jb_solucoes_db.connection.cursor()
            # Adicionamos s.id e s.valor_servico na busca
            query = """
                SELECT s.id, s.titulo_servico, s.descricao_servico, s.status_servico, 
                       m.diagnostico, m.foto_equipamento, s.valor_servico 
                FROM servicos s
                LEFT JOIN manutencoes m ON s.id = m.id_servico
                WHERE s.titulo_servico = %s
            """
            cursor.execute(query, (termo_busca,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                # Extrai apenas o nome do equipamento da descrição completa
                descricao_completa = row[2]
                equipamento_nome = descricao_completa.split('\n')[0].replace('Equipamento: ', '') if descricao_completa else "Não especificado"

                resultado_os = {
                    "id": row[0],
                    "numero_os": row[1],
                    "equipamento": equipamento_nome,
                    "status": row[3],
                    "diagnostico": row[4],
                    "foto": row[5],
                    "valor": row[6] or 0.00 
                }
        except Exception as e:
            print("Erro na busca da OS:", e)
            resultado_os = None

    ferramentas_db = ToolModel.get_all(limit=3)
    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            lista_ferramentas.append(ToolModel.montar_item(f[0], f[1], f[2], f[3]))

    return render_template('landing.html', ferramentas=lista_ferramentas, resultado_os=resultado_os, os_busca=os_busca)

# === 2. TELA DE TRANSIÇÃO / DESTAQUES ===
@app.route("/ferramentas")
def ferramentas_page():
    user_code = session.get("user_code")
    primeiro_nome = "Visitante"
    
    if user_code:
        try:
            cursor = jb_solucoes_db.connection.cursor()
            cursor.execute("SELECT nome FROM pessoas WHERE id = %s", (user_code,))
            row = cursor.fetchone()
            cursor.close()
            
            if row and row[0]:
                primeiro_nome = row[0].split()[0]
        except Exception:
            pass
    elif session.get("user_name"):
        nome_sessao = session.get("user_name")
        if "@" in nome_sessao:
            primeiro_nome = nome_sessao.split("@")[0].capitalize()
        else:
            primeiro_nome = nome_sessao.split()[0]

    ferramentas_db = ToolModel.get_all(limit=3)
    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            lista_ferramentas.append(ToolModel.montar_item(f[0], f[1], f[2], f[3]))

    return render_template('ferramentas.html', ferramentas=lista_ferramentas, usuario_logado=primeiro_nome)


# === 3. CATÁLOGO COMPLETO ===
@app.route('/loja')
def loja_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    ferramentas_db = ToolModel.get_all()
    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            lista_ferramentas.append(ToolModel.montar_item(f[0], f[1], f[2], f[3]))

    return render_template('loja.html', ferramentas=lista_ferramentas)


# === 4. DETALHES DO PRODUTO ===
@app.route('/detalhe/<int:id>')
def detalhe_produto(id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    ferramenta_selecionada = ToolModel.get_by_id(id)
    if ferramenta_selecionada:
        ferramenta_selecionada = ToolModel.montar_item(
            ferramenta_selecionada["id"], ferramenta_selecionada["marca"],
            ferramenta_selecionada["modelo"], ferramenta_selecionada["descricao"])
    return render_template('detalhes.html', ferramenta=ferramenta_selecionada)


# === 5. PROCESSAMENTO DE LOGIN ===
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario") or request.form.get("username")
        senha = request.form.get("senha") or request.form.get("password")

        if UserAccountModel.auth(usuario, senha):
            dados_conta = UserAccountModel.get(usuario)

            if dados_conta and "id_person" in dados_conta:
                id_pessoa = dados_conta["id_person"]
                session['user_code'] = id_pessoa
                session['logged_in'] = True
                session['user_name'] = usuario
                
                try:
                    cursor = jb_solucoes_db.connection.cursor()
                    # BUSCA O PERFIL E A FILIAL
                    cursor.execute("SELECT perfil, id_filial FROM pessoas WHERE id = %s", (id_pessoa,))
                    resultado = cursor.fetchone()
                    cursor.close()
                    
                    if resultado and resultado[0]:
                        perfil = str(resultado[0]).strip().lower()
                        if perfil == 'administrador':
                            perfil = 'admin'
                            
                        session['user_perfil'] = perfil 
                        session['id_filial'] = resultado[1] # <--- Guarda a filial do colaborador
                        
                        if perfil in ['colaborador', 'admin', 'gerente']:
                            session['pode_ver_gerenciador'] = True
                            session['pode_ver_painel'] = True
                        else:
                            session['pode_ver_gerenciador'] = False
                            session['pode_ver_painel'] = False
                    else:
                        session['user_perfil'] = 'cliente'
                        session['id_filial'] = None
                        session['pode_ver_gerenciador'] = False
                        session['pode_ver_painel'] = False
                        
                except Exception as e:
                    print("Erro SQL no Login:", e)
                    session['user_perfil'] = 'cliente'
                    session['id_filial'] = None
                    session['pode_ver_gerenciador'] = False
                    session['pode_ver_painel'] = False

                flash("Login realizado com sucesso!", "success")
                return redirect(url_for('main_page'))

        flash("Usuário ou senha incorretos.", "danger")
        return render_template('index.html')

    return render_template('index.html')


# === 6. PERFIL ===
@app.route('/perfil', methods=['GET', 'POST'])
def perfil_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_code = session.get('user_code')
    status = None
    if request.method == "POST":
        nome = (request.form.get('nome') or '').strip()
        email = (request.form.get('email') or '').strip()
        telefone = (request.form.get('telefone') or '').strip()
        endereco = (request.form.get('endereco') or '').strip()

        if not nome or not email:
            flash("Nome e e-mail são obrigatórios.", "danger")
        elif PersonModel.update(user_code, name=nome, address=endereco, email=email, phone_number=telefone):
            flash("Dados atualizados com sucesso!", "success")
        else:
            flash("Não foi possível salvar os dados. Tente novamente.", "danger")
        return redirect(url_for('perfil_page'))

    try:
        cursor = jb_solucoes_db.connection.cursor()
        cursor.execute("SELECT * FROM pessoas WHERE id = %s", (user_code,))
        colunas = [col[0] for col in cursor.description]
        row = cursor.fetchone()
        cursor.close()
        user_infos = dict(zip(colunas, row)) if row else None
    except Exception:
        user_infos = PersonModel.get(user_code)

    if user_infos is None:
        flash("Erro ao carregar os dados.", "danger")
        return redirect(url_for('loja_page'))

    historico_servicos = ServiceModel.get_user_history(user_code)
    return render_template('perfil.html', user_infos=user_infos, status=status, historico=historico_servicos)


# === 7. CADASTRO (COM LÓGICA DE PRÉ-CADASTRO) ===
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template('register.html')
        
    if request.method == "POST":
        name = (request.form.get('nome') or '').strip()
        user_type_raw = request.form.get('tipo_pessoa') or request.form.get('tipo')
        user_type = 'pj' if user_type_raw in ('juridica', 'pj') else 'pf'
        
        code = somente_numeros(request.form.get('cpf_cnpj') or request.form.get('code'))
        address = (request.form.get('endereco') or '').strip()
        email = (request.form.get('email') or '').strip()
        phone_number = (request.form.get('telefone') or '').strip()
        user = (request.form.get('username') or request.form.get('usuario') or '').strip()
        password = request.form.get('password') or request.form.get('senha') or ''

        if not all([name, code, address, email, phone_number, user, password]):
            flash("Preencha todos os campos.", "danger")
            return render_template('register.html')

        documento_ok = cnpj_valido(code) if user_type == 'pj' else cpf_valido(code)
        if not documento_ok:
            flash("CPF/CNPJ inválido.", "danger")
            return render_template('register.html')

        if UserAccountModel.get(user) is not None:
            flash("Este nome de usuário já está em uso.", "danger")
            return render_template('register.html')

        try:
            cursor = jb_solucoes_db.connection.cursor()
            
            # 1. Verifica se a pessoa já existe (Pré-cadastro)
            cursor.execute("SELECT id FROM pessoas WHERE codigo = %s", (code,))
            pessoa = cursor.fetchone()
            
            if pessoa:
                id_pessoa = pessoa[0]
                # Verifica se já tem um login real associado
                cursor.execute("SELECT id FROM usuarios WHERE id_pessoa = %s", (id_pessoa,))
                if cursor.fetchone():
                    flash("Este CPF/CNPJ já possui uma conta de acesso completa.", "danger")
                    return render_template('register.html')
                else:
                    # ATUALIZA os dados do pré-cadastro com o novo e-mail e endereço
                    cursor.execute("""
                        UPDATE pessoas SET nome = %s, endereco = %s, email = %s, telefone = %s
                        WHERE id = %s
                    """, (name, address, email, phone_number, id_pessoa))
            else:
                # CRIA uma nova pessoa do zero se não houver pré-cadastro
                cursor.execute("""
                    INSERT INTO pessoas (nome, tipo, endereco, email, telefone, codigo)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (name, user_type, address, email, phone_number, code))
                id_pessoa = cursor.lastrowid

            # 2. Cria o utilizador (Login e Senha) com perfil 1 (Cliente)
            hashed_password = jb_bcrypt.generate_password_hash(password).decode("utf-8")
            cursor.execute("""
                INSERT INTO usuarios (nome_usuario, senha, id_pessoa, id_perfil, ativo)
                VALUES (%s, %s, %s, 1, 1)
            """, (user, hashed_password, id_pessoa))
            
            jb_solucoes_db.connection.commit()
            cursor.close()
            
            flash("Conta criada com sucesso! Faça login para ver as suas OS.", "success")
            return redirect(url_for('login'))
            
        except Exception as e:
            print("Erro no cadastro:", e)
            flash("Erro ao processar o cadastro.", "danger")
            return render_template('register.html')


# === 8. LOGOUT ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main_page'))


# === 9. MANUTENÇÃO (CLIENTE) ===
@app.route('/manutencao', methods=['GET', 'POST'])
def manutencao_page():
    if not session.get('logged_in'):
        flash("Por favor, faça login ou cadastre-se para solicitar uma manutenção.", "warning")
        return redirect(url_for('login'))

    if request.method == 'POST':
        description = request.form.get('descricao')
        tool_details = request.form.get('detalhes_equipamento')
        user_id = session.get('user_code')
        sucesso, mensagem = ServiceModel.create_maintenance(user_id, description, tool_details)
        if sucesso:
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")
        return redirect(url_for('perfil_page'))

    return render_template('manutencao.html')


# === 10. ALUGUEL ===
@app.route('/alugar/<int:ferramenta_id>', methods=['POST'])
def alugar_ferramenta(ferramenta_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    ferramenta = ToolModel.get_by_id(ferramenta_id)
    if not ferramenta:
        flash("Ferramenta não encontrada.", "danger")
        return redirect(url_for('loja_page'))

    try:
        dias = max(1, min(30, int(request.form.get('dias_aluguel', 1))))
    except ValueError:
        dias = 1

    diaria = ToolModel.montar_item(ferramenta["id"], ferramenta["marca"], ferramenta["modelo"])["preco"]
    valor_total = round(diaria * dias, 2)
    sucesso, mensagem = ServiceModel.create_rental(user_id, ferramenta_id, dias, valor_total)
    
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('perfil_page'))


# === 11. COMPRA ===
@app.route('/comprar/<int:ferramenta_id>', methods=['POST'])
def comprar_ferramenta(ferramenta_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    ferramenta = ToolModel.get_by_id(ferramenta_id)
    if not ferramenta:
        flash("Ferramenta não encontrada.", "danger")
        return redirect(url_for('loja_page'))

    valor_total = ToolModel.montar_item(ferramenta["id"], ferramenta["marca"], ferramenta["modelo"])["preco"]
    sucesso, mensagem = ServiceModel.create_purchase(user_id, ferramenta_id, valor_total)
    
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('perfil_page'))


# === 12. DASHBOARD / GERENCIADOR ===
@app.route('/colaborador/dashboard')
def colaborador_dashboard():
    if not session.get('logged_in') or not session.get('pode_ver_gerenciador'):
        flash("Acesso restrito à equipa interna e administradores.", "danger")
        return redirect(url_for('login'))
        
    return render_template('gerenciador.html')


# === 12.1 PAINEL DE PEDIDOS / GRÁFICOS ===
@app.route('/colaborador/painel')
def painel_colaborador():
    if not session.get('logged_in') or not session.get('pode_ver_painel'):
        flash("Acesso restrito à equipa interna e administradores.", "danger")
        return redirect(url_for('login'))
        
    servicos_pendentes = ColaboradorModel.get_servicos_pendentes()
    return render_template('pedidos.html', servicos=servicos_pendentes)


# === 13. CRIAR ORDEM DE SERVIÇO ===
@app.route("/colaborador/criar_os", methods=["GET", "POST"])
def criar_os():
    if request.method == "POST":
        try:
            cliente = request.form.get("cliente")
            telefone = request.form.get("telefone")
            equipamento = request.form.get("equipamento")
            num_serie = request.form.get("num_serie", "N/A")
            defeito = request.form.get("defeito")
            
            numero_os = f"OS-{random.randint(10000, 99999)}"
            id_colaborador = session.get('user_code', 1) 
            id_filial_colab = session.get('id_filial') # <--- Carimba a OS com a filial
            
            caminho_foto_banco = None
            fotos = request.files.getlist('fotos_os')
            
            if fotos and fotos[0].filename != '':
                foto = fotos[0]
                pasta_uploads = app.config['UPLOAD_FOLDER']
                
                nome_seguro = secure_filename(foto.filename)
                nome_arquivo = f"{numero_os}_{nome_seguro}"
                
                caminho_salvar = os.path.join(pasta_uploads, nome_arquivo)
                foto.save(caminho_salvar)
                
                caminho_foto_banco = f"uploads/equipamentos/{nome_arquivo}"
            
            cursor = jb_solucoes_db.connection.cursor()
            
            cursor.execute("SELECT id FROM pessoas WHERE telefone = %s OR nome = %s LIMIT 1", (telefone, cliente))
            pessoa_resultado = cursor.fetchone()
            
            if pessoa_resultado:
                id_cliente = pessoa_resultado[0]
            else:
                cursor.execute("""
                    INSERT INTO pessoas (nome, tipo, endereco, email, telefone) 
                    VALUES (%s, 'pf', 'Não informado', 'nao@informado.com', %s)
                """, (cliente, telefone))
                id_cliente = cursor.lastrowid
                
            descricao_completa = f"Equipamento: {equipamento} (Série: {num_serie})\nDefeito Relatado: {defeito}"
            
            # Insere a OS associada à filial
            cursor.execute("""
                INSERT INTO servicos (servico_solicitado, titulo_servico, descricao_servico, status_servico, id_pessoa_solicitante, id_pessoa_abertura, id_filial) 
                VALUES ('manutencao', %s, %s, 'Aberto', %s, %s, %s)
            """, (numero_os, descricao_completa, id_cliente, id_colaborador, id_filial_colab))
            id_servico = cursor.lastrowid
            
            cursor.execute("""
                INSERT INTO manutencoes (diagnostico, garantia, foto_equipamento, id_servico) 
                VALUES ('Aguardando avaliação técnica', 0, %s, %s)
            """, (caminho_foto_banco, id_servico))
            
            jb_solucoes_db.connection.commit()
            cursor.close()
            
            return render_template('criar_os.html', sucesso=True, numero_os=numero_os)
            
        except Exception as e:
            erro_msg = f"Erro no sistema: {str(e)}"
            print(erro_msg)
            flash(erro_msg, "danger")
            return redirect(url_for('criar_os'))
            
    return render_template('criar_os.html')


# === 14. ATUALIZAR ORÇAMENTO ===
@app.route('/colaborador/orcamento/<int:id_servico>', methods=['POST'])
def atualizar_orcamento(id_servico):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    id_colaborador = session.get('user_code')
    valor = request.form.get('valor_servico')
    status = request.form.get('status_servico')
    detalhes_dano = request.form.get('detalhes_dano')
    imagem = request.files.get('imagem_dano')
    caminho_relativo = None
    if imagem and imagem.filename != '':
        nome_arquivo = secure_filename(imagem.filename)
        nome_final = f"manutencao_dano_{id_servico}_{nome_arquivo}"
        caminho_salvar = os.path.join(app.config['UPLOAD_FOLDER'], nome_final)
        imagem.save(caminho_salvar)
        caminho_relativo = f"uploads/equipamentos/{nome_final}"
    sucesso, mensagem = ColaboradorModel.atualizar_orcamento(
        id_servico, id_colaborador, valor, status, caminho_relativo, detalhes_dano
    )
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('painel_colaborador'))


# === 15. CLIENTE RESPONDE ORÇAMENTO ===
@app.route('/cliente/orcamento/<int:id_servico>/<resposta>', methods=['POST'])
def responder_orcamento(id_servico, resposta):
    if not session.get('logged_in'):
        flash("Para aprovar ou recusar este orçamento com segurança, por favor acesse a sua conta ou faça um cadastro rápido.", "warning")
        return redirect(url_for('login'))
        
    novo_status = 'Orçamento Aprovado' if resposta == 'aprovado' else 'Orçamento Recusado'
    numero_os = None
    
    try:
        cursor = jb_solucoes_db.connection.cursor()
        
        cursor.execute("""
            UPDATE servicos 
            SET status_servico = %s 
            WHERE id = %s
        """, (novo_status, id_servico))
        
        cursor.execute("SELECT titulo_servico FROM servicos WHERE id = %s", (id_servico,))
        row = cursor.fetchone()
        if row:
            numero_os = row[0].replace('OS-', '')
            
        jb_solucoes_db.connection.commit()
        cursor.close()
        
        flash(f"Orçamento {resposta.upper()} com sucesso!", "success")
    except Exception as e:
        print("Erro ao responder orçamento:", e)
        flash("Ocorreu um erro ao processar a resposta.", "danger")
        
    if numero_os:
        return redirect(url_for('main_page', os_busca=numero_os))
        
    return redirect(url_for('main_page'))


# === 16. GERENCIAR FERRAMENTAS E EQUIPA (ADMIN E COLABORADOR) ===
@app.route('/admin/ferramentas', methods=['GET', 'POST'])
def gerenciar_ferramentas():
    perfil = session.get('user_perfil')
    if not session.get('logged_in') or perfil not in ['admin', 'administrador', 'colaborador']:
        flash("Acesso restrito. Apenas a equipa interna tem permissão.", "danger")
        return redirect(url_for('main_page'))
        
    if request.method == 'POST':
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        descricao = request.form.get('descricao')
        id_tipo = request.form.get('tipo_ferramenta')
        operacao = request.form.get('operacao')
        
        foto = request.files.get('foto_ferramenta')
        caminho_foto = None
        
        if foto and foto.filename != '':
            nome_seguro = secure_filename(foto.filename)
            nome_final = f"ferramenta_{secrets.token_hex(4)}_{nome_seguro}"
            caminho_salvar = os.path.join(app.config['UPLOAD_FOLDER'], nome_final)
            foto.save(caminho_salvar)
            caminho_foto = f"uploads/equipamentos/{nome_final}"
        
        try:
            cursor = jb_solucoes_db.connection.cursor()
            cursor.execute("""
                INSERT INTO ferramentas (marca, modelo, descricao, id_tipo, operacao, imagem) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (marca, modelo, descricao, id_tipo, operacao, caminho_foto))
            jb_solucoes_db.connection.commit()
            cursor.close()
            flash("Ferramenta cadastrada com sucesso no catálogo!", "success")
        except Exception as e:
            print("Erro ao salvar ferramenta:", e)
            flash("Erro ao registar a ferramenta na base de dados.", "danger")
            
        return redirect(url_for('gerenciar_ferramentas'))
        
    tipos = ToolModel.get_tipos()
    todas_ferramentas = ToolModel.get_all()
    filiais = AdminModel.get_filiais()
    
    try:
        cursor = jb_solucoes_db.connection.cursor()
        cursor.execute("""
            SELECT u.nome_usuario, p.nome, p.codigo, p.perfil, p.telefone
            FROM usuarios u
            JOIN pessoas p ON u.id_pessoa = p.id
            WHERE p.perfil IN ('colaborador', 'admin', 'administrador')
            ORDER BY p.nome ASC
        """)
        equipe = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print("Erro ao buscar equipa:", e)
        equipe = []

    return render_template('painel_ferramentas.html', tipos=tipos, ferramentas=todas_ferramentas, filiais=filiais, equipe=equipe)

# === 16.1 CADASTRAR CONTA DA EQUIPA (ADMIN) ===
@app.route('/admin/equipe', methods=['POST'])
def cadastrar_equipe():
    if not session.get('logged_in') or session.get('user_perfil') not in ['admin', 'administrador']:
        flash("Acesso negado. Apenas administradores podem criar contas para a equipa.", "danger")
        return redirect(url_for('gerenciar_ferramentas'))

    nome = request.form.get('nome')
    cpf = somente_numeros(request.form.get('cpf'))
    email = request.form.get('email')
    telefone = request.form.get('telefone')
    usuario = request.form.get('usuario')
    senha = request.form.get('senha')
    nivel = request.form.get('nivel') # 'colaborador' ou 'admin'
    id_filial = request.form.get('id_filial') # <--- Captura a filial

    try:
        cursor = jb_solucoes_db.connection.cursor()
        
        cursor.execute("SELECT id FROM pessoas WHERE codigo = %s", (cpf,))
        if cursor.fetchone():
            flash("Já existe uma pessoa cadastrada com este CPF/CNPJ.", "danger")
            return redirect(url_for('gerenciar_ferramentas'))
            
        cursor.execute("SELECT id FROM usuarios WHERE nome_usuario = %s", (usuario,))
        if cursor.fetchone():
            flash("Este nome de login já está a ser utilizado por outro membro.", "danger")
            return redirect(url_for('gerenciar_ferramentas'))

        # Insere a Pessoa com a filial
        cursor.execute("""
            INSERT INTO pessoas (nome, tipo, codigo, email, telefone, endereco, perfil, id_filial)
            VALUES (%s, 'pf', %s, %s, %s, 'Sede JB Ferramentas', %s, %s)
        """, (nome, cpf, email, telefone, nivel, id_filial))
        id_pessoa = cursor.lastrowid

        senha_hash = jb_bcrypt.generate_password_hash(senha).decode('utf-8')
        id_perfil = 3 if nivel == 'admin' else 2
        
        cursor.execute("""
            INSERT INTO usuarios (nome_usuario, senha, id_pessoa, id_perfil, ativo)
            VALUES (%s, %s, %s, %s, 1)
        """, (usuario, senha_hash, id_pessoa, id_perfil))

        jb_solucoes_db.connection.commit()
        cursor.close()
        
        flash(f"Conta de {nivel.capitalize()} criada com sucesso para {nome.split()[0]}!", "success")
        
    except Exception as e:
        print("Erro ao cadastrar membro da equipa:", e)
        flash("Ocorreu um erro ao registar a conta na base de dados.", "danger")

    return redirect(url_for('gerenciar_ferramentas'))

# === 17. ADICIONAR PEÇAS ===
@app.route('/colaborador/orcamento/<int:id_servico>/peca', methods=['POST'])
def adicionar_peca_orcamento(id_servico):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    id_estoque_peca = request.form.get('id_estoque_peca')
    quantidade = request.form.get('quantidade', 1)
    sucesso, mensagem = ColaboradorModel.adicionar_peca_manutencao(id_servico, id_estoque_peca, quantidade)
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('painel_colaborador'))


# === 18. CAIXA ===
@app.route('/colaborador/financeiro')
def relatorio_caixa():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    dados_caixa = ColaboradorModel.get_relatorio_caixa()
    return render_template('caixa.html', caixa=dados_caixa)


# === 19. PERFIS ===
@app.route('/admin/perfis', methods=['GET', 'POST'])
def admin_perfis():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        perfil = request.form.get('perfil')
        descricao = request.form.get('descricao')
        sucesso, msg = AdminModel.create_perfil(perfil, descricao)
        flash(msg, "success" if sucesso else "danger")
        return redirect(url_for('admin_perfis'))
    perfis = AdminModel.get_perfis()
    return render_template('admin_perfis.html', perfis=perfis)


# === 20. FILIAIS ===
@app.route('/admin/filiais', methods=['GET', 'POST'])
def admin_filiais():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        codigo = request.form.get('codigo_filial')
        nome = request.form.get('nome')
        endereco = request.form.get('endereco')
        sucesso, msg = AdminModel.create_filial(codigo, nome, endereco)
        flash(msg, "success" if sucesso else "danger")
        return redirect(url_for('admin_filiais'))
    filiais = AdminModel.get_filiais()
    return render_template('admin_filiais.html', filiais=filiais)


# === 21. UNIDADES ===
@app.route('/admin/unidades', methods=['POST'])
def admin_unidades():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    numero_serie = request.form.get('numero_serie')
    id_ferramenta = request.form.get('id_ferramenta')
    id_filial = request.form.get('id_filial')
    sucesso, msg = AdminModel.create_unidade_ferramenta(numero_serie, id_ferramenta, id_filial)
    flash(msg, "success" if sucesso else "danger")
    return redirect(url_for('gerenciar_ferramentas'))


# === 22. PAINEL COM GRÁFICOS ===
@app.route('/colaborador/graficos')
def painel_graficos():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not session.get('pode_ver_painel'):
        flash("Você não tem permissão para ver o painel.", "danger")
        return redirect(url_for('ferramentas_page'))
    dados = PainelModel.get_resumo_mensal()
    return render_template('painel_graficos.html', dados=dados)


# === 23. TELA DE ORÇAMENTOS ===
@app.route("/colaborador/orcamentos")
def orcamentos_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    id_filial = session.get('id_filial') # <--- Puxa a filial da sessão
    
    try:
        cursor = jb_solucoes_db.connection.cursor()
        query = """
            SELECT s.id, s.titulo_servico, p.nome, s.descricao_servico, s.data_abertura, s.status_servico, s.valor_servico, p.telefone
            FROM servicos s
            JOIN pessoas p ON s.id_pessoa_solicitante = p.id
            WHERE s.servico_solicitado = 'manutencao' 
              AND s.status_servico IN ('Aberto', 'Aguardando avaliação técnica', 'Aguardando Orçamento')
              AND (s.id_filial = %s OR %s IS NULL) 
            ORDER BY s.data_abertura DESC
        """
        cursor.execute(query, (id_filial, id_filial)) # <--- Aplica o filtro de filial
        orcamentos_pendentes = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print("Erro ao buscar orçamentos:", e)
        orcamentos_pendentes = []
        
    return render_template('orcamentos.html', orcamentos=orcamentos_pendentes)


# === 24. TELA GERAL DE SERVIÇOS ===
@app.route("/colaborador/servicos")
def servicos_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    id_filial = session.get('id_filial') # <--- Puxa a filial da sessão
    
    try:
        cursor = jb_solucoes_db.connection.cursor()
        query = """
            SELECT s.id, s.titulo_servico, p.nome, s.servico_solicitado, s.status_servico, DATE_FORMAT(s.data_abertura, '%%d/%%m/%%Y %%H:%%i'), s.descricao_servico, s.valor_servico, p.telefone
            FROM servicos s
            JOIN pessoas p ON s.id_pessoa_solicitante = p.id
            WHERE (s.id_filial = %s OR %s IS NULL)
            ORDER BY s.data_abertura DESC
        """
        cursor.execute(query, (id_filial, id_filial)) # <--- Aplica o filtro de filial
        lista_servicos = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print("Erro ao buscar serviços:", e)
        lista_servicos = []
        
    return render_template('servicos.html', servicos=lista_servicos)


# === 25. TELA DE CLIENTES (COLABORADOR) ===
@app.route("/colaborador/clientes", methods=["GET", "POST"])
def gerenciar_clientes():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
        
    cursor = jb_solucoes_db.connection.cursor()
    
    if request.method == "POST":
        nome = request.form.get("nome")
        telefone = request.form.get("telefone")
        codigo = somente_numeros(request.form.get("codigo")) 
        
        try:
            cursor.execute("SELECT id FROM pessoas WHERE codigo = %s", (codigo,))
            if cursor.fetchone():
                flash("Um cliente com este CPF/CNPJ já existe no sistema.", "warning")
            else:
                cursor.execute("""
                    INSERT INTO pessoas (nome, tipo, endereco, email, telefone, codigo) 
                    VALUES (%s, 'pf', 'Não informado', 'nao@informado.com', %s, %s)
                """, (nome, telefone, codigo))
                jb_solucoes_db.connection.commit()
                flash("Cliente pré-cadastrado com sucesso!", "success")
        except Exception as e:
            print("Erro ao criar cliente:", e)
            flash("Erro ao cadastrar cliente.", "danger")
            
        return redirect(url_for('gerenciar_clientes'))
        
    cursor.execute("""
        SELECT p.id, p.nome, p.codigo, p.telefone, p.email,
               (SELECT COUNT(*) FROM servicos WHERE id_pessoa_solicitante = p.id) as total_os,
               (SELECT COUNT(*) FROM usuarios WHERE id_pessoa = p.id) as tem_conta
        FROM pessoas p
        ORDER BY p.nome ASC
    """)
    clientes = cursor.fetchall()
    cursor.close()
    
    return render_template('clientes.html', clientes=clientes)


# === 26. EXCLUSÃO DE CONTA E ANONIMIZAÇÃO (LGPD) ===
@app.route('/perfil/excluir_conta', methods=['POST'])
def excluir_conta_lgpd():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_code = session.get('user_code')
    try:
        cursor = jb_solucoes_db.connection.cursor()
        
        # 1. Anonimiza os dados sensíveis mantendo o histórico de OS e faturas
        cursor.execute("""
            UPDATE pessoas 
            SET nome = 'Cliente Excluído (LGPD)', 
                endereco = 'Anonimizado', 
                email = 'anonimizado@lgpd.com', 
                telefone = '00000000000', 
                codigo = '00000000000'
            WHERE id = %s
        """, (user_code,))

        # 2. Desativa o acesso ao sistema
        cursor.execute("""
            UPDATE usuarios 
            SET ativo = 0, senha = 'lgpd_deleted_account'
            WHERE id_pessoa = %s
        """, (user_code,))

        jb_solucoes_db.connection.commit()
        cursor.close()

        # Limpa a sessão (faz logout)
        session.clear()
        flash("A sua conta e dados pessoais foram excluídos com sucesso, em conformidade com a LGPD.", "success")
        return redirect(url_for('main_page'))
        
    except Exception as e:
        print("Erro na exclusão LGPD:", e)
        flash("Ocorreu um erro ao processar a exclusão. Contacte o suporte.", "danger")
        return redirect(url_for('perfil_page'))


if __name__ == "__main__":
    app.run(debug=True)