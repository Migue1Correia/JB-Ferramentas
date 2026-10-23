import os
import secrets
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
from validacao import somente_numeros, cpf_valido, cnpj_valido, pode_ver_painel

from dotenv import load_dotenv

# Carrega as configurações do arquivo .env (que NÃO vai para o GitHub).
# Use o arquivo .env.example como modelo.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

app = Flask(__name__)

app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER', 'root')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD', '')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB', 'jb_ferramentas')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_PORT', '3306'))

# Chave que protege a sessão de login. Se o .env não tiver uma chave própria, o sistema
# cria uma aleatória (segura, mas todo mundo precisa logar de novo a cada reinício).
chave_secreta = os.getenv('SECRET_KEY', '')
if not chave_secreta or chave_secreta.startswith('troque'):
    print("AVISO: defina SECRET_KEY no arquivo .env. Usando uma chave temporária.")
    chave_secreta = secrets.token_hex(32)
app.config['SECRET_KEY'] = chave_secreta

# Proteção CSRF: todo formulário (POST) precisa enviar o campo escondido csrf_token.
csrf = CSRFProtect(app)

UPLOAD_FOLDER = os.path.join(
    app.root_path, 'static', 'uploads', 'equipamentos')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)


@app.errorhandler(CSRFError)
def formulario_expirado(erro):
    """Quando o csrf_token falta ou venceu, volta para a tela anterior com um aviso."""
    flash("O formulário expirou. Tente enviar de novo.", "danger")
    return redirect(request.referrer or url_for('login'))


def pode_ver_painel():
    """Diz se o usuário atual pode ver o painel de gráficos (e o card dele nos menus)."""
    return bool(session.get('logged_in'))


@app.context_processor
def variaveis_dos_menus():
    """Deixa a variável pode_ver_painel disponível em todos os templates."""
    return {"pode_ver_painel": pode_ver_painel()}


@app.template_filter('moeda')
def formatar_moeda(valor):
    """Formata um número como dinheiro no padrão brasileiro. Ex.: 1234.5 -> R$ 1.234,50"""
    texto = f"{float(valor or 0):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


# === 1. TELA INICIAL (LANDING PAGE) COM BUSCA DE OS ===
@app.route("/", methods=['GET'])
def main_page():
    os_busca = request.args.get('os_busca')
    resultado_os = None
    
    if os_busca:
        try:
            cursor = jb_solucoes_db.connection.cursor()
            # Consulta adaptada para MySQL (%s em vez de ?)
            cursor.execute("SELECT id, ferramenta, modelo, marca, status FROM ordens_servico WHERE id = %s", (os_busca,))
            row = cursor.fetchone()
            cursor.close()
            
            if row:
                resultado_os = {
                    "id": row[0],
                    "ferramenta": row[1],
                    "modelo": row[2],
                    "marca": row[3],
                    "status": row[4]  # Ex: "Em manutenção", "Aguardando peça", "Aguardando orçamento", "Pronta para retirar"
                }
        except Exception as e:
            # Caso a tabela ordens_servico ainda não exista no banco, evita quebrar a página
            resultado_os = None

    # Carrega as ferramentas em destaque para a landing page
    ferramentas_db = ToolModel.get_all(limit=3)
    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            lista_ferramentas.append(
                ToolModel.montar_item(f[0], f[1], f[2], f[3]))

    return render_template('landing.html', ferramentas=lista_ferramentas, resultado_os=resultado_os, os_busca=os_busca)


# === 2. TELA DE TRANSIÇÃO / DESTAQUES DE SERVIÇOS ===
@app.route("/ferramentas")
def ferramentas_page():
    usuario_logado = session.get("user_name")
    ferramentas_db = ToolModel.get_all(limit=3)

    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            lista_ferramentas.append(
                ToolModel.montar_item(f[0], f[1], f[2], f[3]))

    return render_template('ferramentas.html', ferramentas=lista_ferramentas, usuario_logado=usuario_logado)


# === 3. CATÁLOGO COMPLETO DA LOJA ===
@app.route('/loja')
def loja_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    ferramentas_db = ToolModel.get_all()
    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            lista_ferramentas.append(
                ToolModel.montar_item(f[0], f[1], f[2], f[3]))

    return render_template('loja.html', ferramentas=lista_ferramentas)


# === 4. DETALHES DO PRODUTO SELECIONADO ===
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


## === 5. PROCESSAMENTO DE LOGIN ===
# === 5. PROCESSAMENTO DE LOGIN ===
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario") or request.form.get("username")
        senha = request.form.get("senha") or request.form.get("password")

        if UserAccountModel.auth(usuario, senha):
            dados_conta = UserAccountModel.get(usuario)

            if dados_conta and "id_person" in dados_conta:
                session['user_code'] = dados_conta["id_person"]
                session['logged_in'] = True
                session['user_name'] = usuario
                flash("Login realizado com sucesso!", "success")
                
                # Todos os usuários vão para a página inicial unificada
                return redirect(url_for('main_page'))

        flash("Usuário ou senha incorretos.", "danger")
        return render_template('index.html')

    return render_template('index.html')


# === NOVA ROTA DO PAINEL DO COLABORADOR ===
@app.route('/colaborador/dashboard')
def colaborador_dashboard():
    if not session.get('logged_in') or session.get('user_perfil') not in ('Colaborador', 'colaborador'):
        flash("Acesso restrito a colaboradores.", "danger")
        return redirect(url_for('login'))
        
    return render_template('gerenciador.html')


# === 6. TELA DE PERFIL DO USUÁRIO ===
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


# === 7. CADASTRO DE USUÁRIOS ===
@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == "GET":
        return render_template('register.html')
        
    if request.method == "POST":
        name = (request.form.get('nome') or '').strip()
        
        user_type_raw = request.form.get('tipo_pessoa') or request.form.get('tipo')
        if user_type_raw in ('fisica', 'pf'):
            user_type = 'pf'
        elif user_type_raw in ('juridica', 'pj'):
            user_type = 'pj'
        else:
            flash("Tipo de pessoa inválido.", "danger")
            return render_template('register.html')

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
            msg_erro = "CNPJ inválido." if user_type == 'pj' else "CPF inválido."
            flash(msg_erro, "danger")
            return render_template('register.html')

        if PersonModel.exist(code, by="code"):
            flash("CPF/CNPJ já cadastrado.", "danger")
            return render_template('register.html')

        if UserAccountModel.get(user) is not None:
            flash("Este nome de usuário já está em uso.", "danger")
            return render_template('register.html')

        if not PersonModel.create(name, user_type, code, address, email, phone_number):
            flash("Erro no cadastro.", "danger")
            return render_template('register.html')

        person_infos = PersonModel.get(code)
        hashed_password = jb_bcrypt.generate_password_hash(
            password).decode("utf-8")

        if not UserAccountModel.create(user, hashed_password, person_infos["id"], 1, True):
            PersonModel.delete(person_infos["id"])
            flash("Erro ao criar a conta. Tente novamente.", "danger")
            return render_template('register.html')

        flash("Cadastro realizado com sucesso!", "success")
        return redirect(url_for('login'))


# === 8. LOGOUT ===
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('main_page'))


# === 9. ROTA DE MANUTENÇÃO ===
@app.route('/manutencao', methods=['GET', 'POST'])
def manutencao_page():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        description = request.form.get('descricao')
        tool_details = request.form.get('detalhes_equipamento')
        user_id = session.get('user_code')
        sucesso, mensagem = ServiceModel.create_maintenance(
            user_id, description, tool_details)
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

    diaria = ToolModel.montar_item(
        ferramenta["id"], ferramenta["marca"], ferramenta["modelo"])["preco"]
    valor_total = round(diaria * dias, 2)
    sucesso, mensagem = ServiceModel.create_rental(
        user_id, ferramenta_id, dias, valor_total)
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

    valor_total = ToolModel.montar_item(
        ferramenta["id"], ferramenta["marca"], ferramenta["modelo"])["preco"]
    sucesso, mensagem = ServiceModel.create_purchase(
        user_id, ferramenta_id, valor_total)
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('perfil_page'))


# === 12. PAINEL COLABORADOR ===
@app.route('/colaborador/painel')
def painel_colaborador():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    servicos_pendentes = ColaboradorModel.get_servicos_pendentes()
    return render_template('painel_colaborador.html', servicos=servicos_pendentes)


# === 13. ATUALIZAR ORÇAMENTO ===
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


# === 14. CLIENTE RESPONDE ORÇAMENTO ===
@app.route('/cliente/orcamento/<int:id_servico>/<resposta>', methods=['POST'])
def responder_orcamento(id_servico, resposta):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    sucesso, mensagem = ServiceModel.responder_orcamento(
        id_servico, user_id, resposta)
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('perfil_page'))


# === 15. GERENCIAR FERRAMENTAS ===
@app.route('/colaborador/ferramentas', methods=['GET', 'POST'])
def gerenciar_ferramentas():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if request.method == 'POST':
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        descricao = request.form.get('descricao')
        id_tipo = request.form.get('tipo_ferramenta')
        sucesso, mensagem = ToolModel.create(marca, modelo, descricao, id_tipo)
        if sucesso:
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")
        return redirect(url_for('gerenciar_ferramentas'))
    tipos = ToolModel.get_tipos()
    todas_ferramentas = ToolModel.get_all()
    filiais = AdminModel.get_filiais()
    return render_template('painel_ferramentas.html', tipos=tipos, ferramentas=todas_ferramentas, filiais=filiais)


# === 16. ADICIONAR PEÇAS ===
@app.route('/colaborador/orcamento/<int:id_servico>/peca', methods=['POST'])
def adicionar_peca_orcamento(id_servico):
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    id_estoque_peca = request.form.get('id_estoque_peca')
    quantidade = request.form.get('quantidade', 1)
    sucesso, mensagem = ColaboradorModel.adicionar_peca_manutencao(
        id_servico, id_estoque_peca, quantidade)
    if sucesso:
        flash(mensagem, "success")
    else:
        flash(mensagem, "danger")
    return redirect(url_for('painel_colaborador'))


# === 17. CAIXA ===
@app.route('/colaborador/financeiro')
def relatorio_caixa():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    dados_caixa = ColaboradorModel.get_relatorio_caixa()
    return render_template('caixa.html', caixa=dados_caixa)


# === 18. PERFIS ===
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


# === 19. FILIAIS ===
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


# === 20. UNIDADES ===
@app.route('/admin/unidades', methods=['POST'])
def admin_unidades():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    numero_serie = request.form.get('numero_serie')
    id_ferramenta = request.form.get('id_ferramenta')
    id_filial = request.form.get('id_filial')
    sucesso, msg = AdminModel.create_unidade_ferramenta(
        numero_serie, id_ferramenta, id_filial)
    flash(msg, "success" if sucesso else "danger")
    return redirect(url_for('gerenciar_ferramentas'))


# === 21. PAINEL COM GRÁFICOS ===
@app.route('/colaborador/graficos')
def painel_graficos():
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    if not pode_ver_painel():
        flash("Você não tem permissão para ver o painel.", "danger")
        return redirect(url_for('ferramentas_page'))
    dados = PainelModel.get_resumo_mensal()
    return render_template('painel_graficos.html', dados=dados)


if __name__ == "__main__":
    app.run(debug=True)