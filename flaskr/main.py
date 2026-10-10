import os
import hashlib
import secrets
from datetime import datetime, timedelta
from uuid import uuid4
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.utils import secure_filename
from flasgger import Swagger
from flask_wtf.csrf import CSRFProtect, CSRFError
from model.db import jb_solucoes_db, jb_bcrypt
from model.user_account import UserAccountModel
from model.person import PersonModel
from model.toolmodel import ToolModel
from model.service import ServiceModel, PAGAMENTO_PENDENTE, PAGAMENTO_RETIRADA
from model.colaborador import ColaboradorModel
from model.admin import AdminModel
from model.painel import PainelModel
from validacao import somente_numeros, cpf_valido, cnpj_valido

from dotenv import load_dotenv

# Carrega as configurações do arquivo .env (que NÃO vai para o GitHub).
# Use o arquivo .env.example como modelo.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'))

app = Flask(__name__)
swagger = Swagger(app, template={"info": {
    "title": "JB Ferramentas",
    "version": "1.0",
    "description": "Rotas do sistema. As rotas POST exigem o campo csrf_token dos formulários do site, "
                   "por isso o botão \"Try it out\" não funciona para elas: use esta página para consulta.",
}})

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

# Cookie da sessão: não é enviado em pedidos vindos de outros sites e, com COOKIE_SO_HTTPS=1
# no .env (quando o site estiver em HTTPS), nunca trafega sem criptografia.
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_SECURE'] = os.getenv('COOKIE_SO_HTTPS') == '1'

# Proteção CSRF: todo formulário (POST) precisa enviar o campo escondido csrf_token.
# Isso impede que outro site envie formulários em nome de um usuário logado.
# O csrf_token vale enquanto durar a sessão (o padrão seria vencer em 1 hora,
# e quem deixasse a tela aberta perderia o que digitou)
app.config['WTF_CSRF_TIME_LIMIT'] = None
csrf = CSRFProtect(app)

UPLOAD_FOLDER = os.path.join(
    app.root_path, 'static', 'uploads', 'equipamentos')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Fotos enviadas: no máximo 5 MB, para ninguém encher o disco do servidor
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

# O banco trabalha sempre no horário de Brasília, mesmo se o servidor estiver em outro fuso
app.config['MYSQL_CUSTOM_OPTIONS'] = {'init_command': "SET time_zone = '-03:00'"}

jb_solucoes_db.init_app(app)
jb_bcrypt.init_app(app)


@app.errorhandler(CSRFError)
def formulario_expirado(erro):
    """Quando o csrf_token falta ou venceu, volta para a tela inicial com um aviso."""
    flash("O formulário expirou. Tente enviar de novo.", "danger")
    return redirect(url_for('ferramentas_page'))


@app.errorhandler(413)
def arquivo_grande_demais(erro):
    return "A foto pode ter no máximo 5 MB. Volte e envie um arquivo menor.", 413


@app.errorhandler(404)
def pagina_nao_encontrada(erro):
    return render_template('erro.html', titulo="Página não encontrada",
                           mensagem="O endereço que você abriu não existe ou foi removido."), 404


@app.errorhandler(500)
def erro_interno(erro):
    return render_template('erro.html', titulo="Algo deu errado",
                           mensagem="Tivemos um problema ao abrir esta página. Tente de novo em instantes."), 500


@app.before_request
def proteger_areas_restritas():
    """
    Telas de colaborador/administrador e documentação da API (Swagger):
    só para quem está logado com perfil de colaborador. Vale para todas as rotas
    que começam com /colaborador ou /admin, então rota nova já nasce protegida.
    """
    # Relê o perfil no banco a cada página: quem foi rebaixado perde o acesso (e o card
    # do painel no menu) na hora, sem precisar sair
    if session.get('logged_in') and request.endpoint != 'static':
        perfil, senha = UserAccountModel.get_perfil_e_senha(session.get('user_name'))
        # A sessão acaba aqui se a conta foi desativada ou apagada, ou se a senha foi trocada
        # depois deste login (assim, trocar a senha derruba quem estava logado em outro lugar)
        if perfil is None or marca_da_senha(senha) != session.get('marca'):
            session.clear()
            flash("Sua sessão não é mais válida. Entre de novo.", "danger")
            return redirect(url_for('login'))
        session['perfil'] = perfil

    if request.path.startswith(('/colaborador', '/admin', '/apidocs', '/apispec', '/flasgger_static')):
        if not session.get('logged_in'):
            return redirect(url_for('login'))
        if not pode_ver_painel():
            flash("Você não tem permissão para acessar essa área.", "danger")
            return redirect(url_for('ferramentas_page'))
        # Tudo que começa com /admin (perfis e filiais) é só do Administrador
        if request.path.startswith('/admin') and not eh_administrador():
            flash("Só o Administrador acessa essa área.", "danger")
            return redirect(url_for('painel_colaborador'))


def marca_da_senha(senha_em_hash):
    """
    Um resumo curto da senha guardada no banco. Fica na sessão para sabermos, a cada página,
    se a senha ainda é a mesma do momento do login. Não dá para descobrir a senha por ele.
    """
    return hashlib.sha256(senha_em_hash.encode("utf-8")).hexdigest()[:16]


def salvar_imagem(arquivo, prefixo):
    """
    Salva uma imagem enviada por formulário na pasta de uploads.
    :return: o caminho para usar com url_for('static'), None se não veio arquivo,
             ou False se o arquivo não for uma imagem.
    """
    if not arquivo or arquivo.filename == '':
        return None
    nome_arquivo = secure_filename(arquivo.filename)
    # Só imagem: a pasta de uploads é pública, um .html aqui viraria uma página do site
    if os.path.splitext(nome_arquivo)[1].lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
        return False
    # O trecho aleatório evita que duas fotos com o mesmo nome se sobrescrevam
    nome_final = f"{prefixo}_{uuid4().hex[:8]}_{nome_arquivo}"
    arquivo.save(os.path.join(app.config['UPLOAD_FOLDER'], nome_final))
    return f"uploads/equipamentos/{nome_final}"


def apagar_imagem(caminho):
    """Apaga uma imagem salva pelo salvar_imagem (usado quando o resto do formulário é recusado)."""
    if caminho:
        os.remove(os.path.join(app.static_folder, caminho))


PERFIL_CLIENTE = "Cliente"
PERFIL_ADMINISTRADOR = "Administrador"
# Perfis que entram nas telas de colaborador. Qualquer outro perfil é tratado como cliente.
PERFIS_COLABORADOR = (PERFIL_ADMINISTRADOR, "Colaborador")


def pode_ver_painel():
    """
    Diz se o usuário atual pode ver as telas de colaborador (e o card do painel nos menus).
    Pode quem está logado com um dos perfis de PERFIS_COLABORADOR.
    O perfil fica na sessão: é lido no login e relido do banco a cada página.
    """
    return bool(session.get('logged_in')) and session.get('perfil') in PERFIS_COLABORADOR


# shortcut: as tentativas de login ficam na memória deste processo (zeram ao reiniciar e não são
# compartilhadas entre processos); passar para uma tabela se o site rodar em mais de um processo.
# shortcut: atrás de um proxy todos chegam com o IP do proxy; nesse caso ler o cabeçalho X-Forwarded-For.
TENTATIVAS_DE_LOGIN = {}
MAX_TENTATIVAS = 5
TEMPO_DE_BLOQUEIO = timedelta(minutes=5)


def login_bloqueado(usuario):
    """Diz se o usuário errou a senha MAX_TENTATIVAS vezes nos últimos minutos."""
    erros, primeiro_erro = TENTATIVAS_DE_LOGIN.get(usuario, (0, None))
    if primeiro_erro and datetime.now() - primeiro_erro > TEMPO_DE_BLOQUEIO:
        TENTATIVAS_DE_LOGIN.pop(usuario, None)
        return False
    return erros >= MAX_TENTATIVAS


def registrar_erro_de_login(usuario):
    if len(TENTATIVAS_DE_LOGIN) > 10000:  # não deixa a lista crescer sem fim
        TENTATIVAS_DE_LOGIN.clear()
    erros, primeiro_erro = TENTATIVAS_DE_LOGIN.get(usuario, (0, None))
    TENTATIVAS_DE_LOGIN[usuario] = (erros + 1, primeiro_erro or datetime.now())


def eh_administrador():
    return bool(session.get('logged_in')) and session.get('perfil') == PERFIL_ADMINISTRADOR


@app.context_processor
def variaveis_dos_menus():
    """
    Deixa disponível em todos os templates: pode_ver_painel, eh_administrador, a quantidade de itens no carrinho
    e para onde vai o card "Manutenção" do menu: o colaborador vai para a tela Serviços,
    o cliente vai para o pedido de manutenção.
    """
    colaborador = pode_ver_painel()
    return {
        "pode_ver_painel": colaborador,
        "eh_administrador": eh_administrador(),
        "itens_no_carrinho": len(session.get('carrinho', [])),
        "link_manutencao": url_for('painel_colaborador' if colaborador else 'manutencao_page'),
    }


@app.template_filter('moeda')
def formatar_moeda(valor):
    """Formata um número como dinheiro no padrão brasileiro. Ex.: 1234.5 -> R$ 1.234,50"""
    texto = f"{float(valor or 0):,.2f}"
    return "R$ " + texto.replace(",", "X").replace(".", ",").replace("X", ".")


# === 1. TELA INICIAL (LANDING PAGE) ===
@app.route("/")
def main_page():
    """
    Página Inicial
    Retorna a landing page do sistema.
    ---
    tags:
      - Público
    responses:
      200:
        description: HTML da página inicial.
    """
    return render_template('landing.html')


# === 2. TELA DE TRANSIÇÃO / DESTAQUES DE SERVIÇOS ===
@app.route("/ferramentas")
def ferramentas_page():
    """
    Destaques de Ferramentas
    Exibe uma vitrine com até 4 ferramentas em destaque.
    ---
    tags:
      - Público
    responses:
      200:
        description: HTML da vitrine.
    """
    usuario_logado = session.get("user_name")
    lista_ferramentas = ToolModel.get_all(limit=4)

    return render_template('ferramentas.html', ferramentas=lista_ferramentas, usuario_logado=usuario_logado)


# === 3. CATÁLOGO COMPLETO DA LOJA ===
@app.route('/loja')
def loja_page():
    """
    Catálogo Completo
    Exibe todas as ferramentas disponíveis na loja.
    ---
    tags:
      - Loja e Produtos
    responses:
      200:
        description: HTML do catálogo.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    lista_ferramentas = ToolModel.get_all()
    return render_template('loja.html', ferramentas=lista_ferramentas)


# === 4. DETALHES DO PRODUTO SELECIONADO ===
@app.route('/detalhe/<int:id>')
def detalhe_produto(id):
    """
    Detalhes do Produto
    Retorna os detalhes de uma ferramenta específica.
    ---
    tags:
      - Loja e Produtos
    parameters:
      - name: id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Detalhes da ferramenta.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    ferramenta_selecionada = ToolModel.get_by_id(id)
    if not ferramenta_selecionada:
        abort(404)
    em_estoque = ServiceModel.get_unidade_disponivel(id) is not None
    return render_template('detalhes.html', ferramenta=ferramenta_selecionada, em_estoque=em_estoque)


# === 5. PROCESSAMENTO DE LOGIN ===
@app.route("/login", methods=["GET", "POST"])
def login():
    """
    Autenticação
    Faz o login do cliente ou colaborador no sistema.
    ---
    tags:
      - Autenticação
    parameters:
      - name: usuario
        in: formData
        type: string
        required: false
      - name: senha
        in: formData
        type: string
        required: false
    responses:
      200:
        description: Página de login.
    """
    if request.method == "POST":
        usuario = request.form.get("usuario") or ""
        senha = request.form.get("senha") or ""
        # A contagem é por usuário E por endereço (IP): quem erra de propósito trava só a si mesmo
        chave = f"{usuario.strip().lower()}|{request.remote_addr}"

        if login_bloqueado(chave):
            return render_template('index.html', status="Muitas tentativas. Aguarde 5 minutos e tente de novo.")

        if UserAccountModel.auth(usuario, senha):
            dados_conta = UserAccountModel.get(usuario)

            if dados_conta and "id_person" in dados_conta:
                session.clear()  # não herda carrinho nem dados de quem usou o navegador antes
                session['user_code'] = dados_conta["id_person"]
                session['logged_in'] = True
                session['user_name'] = dados_conta["username"]  # como está no banco, não como foi digitado
                session['marca'] = marca_da_senha(dados_conta["password"])
                TENTATIVAS_DE_LOGIN.pop(chave, None)
                session['perfil'] = UserAccountModel.get_perfil(usuario)
                flash("Login realizado com sucesso!", "success")
                return redirect(url_for('ferramentas_page'))

        registrar_erro_de_login(chave)
        return render_template('index.html', status="Usuário ou senha incorretos.")

    return render_template('index.html')


# === 6. TELA DE PERFIL DO USUÁRIO ===
@app.route('/perfil', methods=['GET', 'POST'])
def perfil_page():
    """
    Perfil do Cliente
    Exibe os dados e o histórico de serviços.
    ---
    tags:
      - Conta do Cliente
    responses:
      200:
        description: HTML do perfil.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    user_code = session.get('user_code')
    status = None
    if request.method == "POST":
        nome = (request.form.get('nome') or '').strip()
        email = (request.form.get('email') or '').strip()
        telefone = (request.form.get('telefone') or '').strip()
        endereco = (request.form.get('endereco') or '').strip()

        # O CPF/CNPJ não é alterado por aqui (o campo é só leitura).
        if not all([nome, email, telefone, endereco]):
            flash("Preencha nome, e-mail, telefone e endereço.", "danger")
        elif PersonModel.update(user_code, name=nome, address=endereco, email=email, phone_number=telefone):
            flash("Dados atualizados com sucesso!", "success")
        else:
            flash("Não foi possível salvar os dados. Tente novamente.", "danger")
        return redirect(url_for('perfil_page'))

    cursor = jb_solucoes_db.connection.cursor()
    cursor.execute("SELECT * FROM pessoas WHERE id = %s", (user_code,))
    colunas = [col[0] for col in cursor.description]
    row = cursor.fetchone()
    cursor.close()
    user_infos = dict(zip(colunas, row)) if row else None

    if user_infos is None:
        flash("Erro ao carregar os dados.", "danger")
        return redirect(url_for('loja_page'))

    historico_servicos = ServiceModel.get_user_history(user_code)
    return render_template('perfil.html', user_infos=user_infos, status=status, historico=historico_servicos)


@app.route('/perfil/senha', methods=['POST'])
def alterar_senha():
    """
    Alterar Senha
    O usuário logado troca a própria senha, informando a senha atual.
    ---
    tags:
      - Conta do Cliente
    parameters:
      - name: senha_atual
        in: formData
        type: string
      - name: nova_senha
        in: formData
        type: string
      - name: confirmar_senha
        in: formData
        type: string
    responses:
      302:
        description: Volta para o perfil.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    usuario = session.get('user_name')
    nova = request.form.get('nova_senha') or ''
    nova_em_hash = jb_bcrypt.generate_password_hash(nova).decode("utf-8")
    chave = f"{usuario.lower()}|{request.remote_addr}"  # o mesmo contador de erros do login

    if login_bloqueado(chave):
        flash("Muitas tentativas. Aguarde 5 minutos e tente de novo.", "danger")
    elif not UserAccountModel.auth(usuario, request.form.get('senha_atual')):
        registrar_erro_de_login(chave)
        flash("A senha atual não confere.", "danger")
    elif len(nova) < 8:
        flash("A nova senha precisa ter pelo menos 8 caracteres.", "danger")
    elif nova != request.form.get('confirmar_senha'):
        flash("A confirmação não é igual à nova senha.", "danger")
    elif UserAccountModel.mudar_senha(usuario, nova_em_hash):
        TENTATIVAS_DE_LOGIN.pop(chave, None)
        session['marca'] = marca_da_senha(nova_em_hash)  # este navegador continua logado; os outros caem
        flash("Senha alterada com sucesso!", "success")
    else:
        flash("Não foi possível alterar a senha. Tente novamente.", "danger")
    return redirect(url_for('perfil_page'))


# === 7. CADASTRO DE USUÁRIOS ===
@app.route("/register", methods=['GET', 'POST'])
def register():
    """
    Cadastro
    Cria nova conta no sistema.
    ---
    tags:
      - Autenticação
    parameters:
      - name: nome
        in: formData
        type: string
      - name: usuario
        in: formData
        type: string
      - name: senha
        in: formData
        type: string
    responses:
      200:
        description: Status do cadastro.
    """
    if request.method == "GET":
        return render_template('register.html')
    if request.method == "POST":
        name = (request.form.get('nome') or '').strip()
        user_type = request.form.get('tipo')
        code = somente_numeros(request.form.get('code'))  # guarda só os números do CPF/CNPJ
        address = (request.form.get('endereco') or '').strip()
        email = (request.form.get('email') or '').strip()
        phone_number = (request.form.get('telefone') or '').strip()
        user = (request.form.get('usuario') or '').strip()
        password = request.form.get('senha') or ''

        # 1. Confere tudo ANTES de gravar qualquer coisa no banco
        if user_type not in ('pf', 'pj'):
            return render_template('register.html', status="Tipo de pessoa inválido.")

        if not all([name, code, address, email, phone_number, user, password]):
            return render_template('register.html', status="Preencha todos os campos.")

        if len(password) < 8:
            return render_template('register.html', status="A senha precisa ter pelo menos 8 caracteres.")

        # Tamanhos máximos que o banco aceita (o endereço chega já com o número e o CEP juntos)
        for campo, valor, maximo in (("nome", name, 100), ("endereço (contando número e CEP)", address, 200),
                                     ("e-mail", email, 100), ("telefone", phone_number, 20), ("usuário", user, 100)):
            if len(valor) > maximo:
                return render_template('register.html', status=f"O campo {campo} aceita no máximo {maximo} caracteres.")

        documento_ok = cnpj_valido(code) if user_type == 'pj' else cpf_valido(code)
        if not documento_ok:
            status = "CNPJ inválido." if user_type == 'pj' else "CPF inválido."
            return render_template('register.html', status=status)

        if PersonModel.exist(code, by="code"):
            status = "CPF/CNPJ já cadastrado."
            return render_template('register.html', status=status)

        if UserAccountModel.get(user) is not None:
            return render_template('register.html', status="Este nome de usuário já está em uso.")

        # 2. Grava a pessoa e depois a conta de usuário
        if not PersonModel.create(name, user_type, code, address, email, phone_number):
            status = "Erro no cadastro."
            return render_template('register.html', status=status)

        person_infos = PersonModel.get(code)
        hashed_password = jb_bcrypt.generate_password_hash(
            password).decode("utf-8")

        # Todo cadastro feito pelo site entra com o perfil "Cliente"
        id_perfil = UserAccountModel.id_do_perfil(PERFIL_CLIENTE)
        if not id_perfil or not UserAccountModel.create(user, hashed_password, person_infos["id"], id_perfil, True):
            # Se a conta falhar, apaga a pessoa para não sobrar cadastro sem login
            PersonModel.delete(person_infos["id"])
            status = "Erro ao criar a conta. Tente novamente."
            return render_template('register.html', status=status)

        flash("Cadastro realizado com sucesso! Faça o seu login.", "success")
        return redirect(url_for('login'))


# === 8. LOGOUT ===
@app.route('/logout', methods=['POST'])
def logout():
    """
    Sair
    Encerra a sessão atual.
    ---
    tags:
      - Autenticação
    responses:
      302:
        description: Redireciona para home.
    """
    session.clear()
    return redirect(url_for('main_page'))


# === 9. ROTA DE MANUTENÇÃO ===
@app.route('/manutencao', methods=['GET', 'POST'])
def manutencao_page():
    """
    Solicitar Manutenção
    Abre OS para conserto.
    ---
    tags:
      - Serviços e Pedidos (Cliente)
    parameters:
      - name: descricao
        in: formData
        type: string
      - name: detalhes_equipamento
        in: formData
        type: string
    responses:
      200:
        description: Form de manutenção.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        description = (request.form.get('descricao') or '').strip()
        tool_details = (request.form.get('detalhes_equipamento') or '').strip()
        if not description or not tool_details:
            flash("Informe a ferramenta e a descrição do problema.", "danger")
            return redirect(url_for('manutencao_page'))
        if len(tool_details) > 200:
            flash("O nome da ferramenta aceita no máximo 200 caracteres.", "danger")
            return redirect(url_for('manutencao_page'))
        user_id = session.get('user_code')
        sucesso, mensagem = ServiceModel.create_maintenance(
            user_id, description, tool_details)
        if sucesso:
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")
        return redirect(url_for('perfil_page'))

    return render_template('manutencao.html', resumo=ServiceModel.get_resumo_manutencoes(session.get('user_code')))


# === 10. CARRINHO ===
def itens_do_carrinho():
    """
    Monta os itens do carrinho com nome, tipo e valor. O carrinho fica guardado na sessão
    como uma lista de {"id": id da ferramenta, "dias": dias de aluguel ou None se for compra}
    ou {"servico": id da manutenção aprovada que o cliente vai pagar}.
    O valor é sempre calculado aqui no servidor (no aluguel, diária x dias),
    para ninguém conseguir alterar o preço pelo navegador.
    """
    itens = []
    for entrada in session.get('carrinho', []):
        if "servico" in entrada:
            # Pagamento de uma manutenção aprovada: o valor vem do orçamento gravado no banco
            orcamento = ServiceModel.get_orcamento(entrada["servico"], session.get('user_code'))
            if not orcamento or orcamento["pagamento"] != PAGAMENTO_PENDENTE:
                continue
            item = {"servico": orcamento["id"], "nome": f"Manutenção #{orcamento['id']}",
                    "dias": None, "valor": float(orcamento["valor"])}
        else:
            item = ToolModel.get_by_id(entrada["id"])
            if not item:
                continue
            item["dias"] = entrada["dias"]
            item["valor"] = round(item["preco"] * (entrada["dias"] or 1), 2)
        item["entrada"] = entrada
        itens.append(item)

    # O que deixou de existir (ou já foi pago) sai do carrinho guardado também
    session['carrinho'] = [i["entrada"] for i in itens]
    return itens


def por_servico_no_carrinho(id_servico):
    """Coloca o pagamento de uma manutenção no carrinho (sem repetir)."""
    carrinho = session.get('carrinho', [])
    if {"servico": id_servico} not in carrinho:
        carrinho.append({"servico": id_servico})
        session['carrinho'] = carrinho


@app.route('/carrinho')
def carrinho_page():
    """
    Carrinho
    Lista os itens que o cliente escolheu e o valor total.
    ---
    tags:
      - Serviços e Pedidos (Cliente)
    responses:
      200:
        description: HTML do carrinho.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    itens = itens_do_carrinho()
    return render_template('carrinho.html', itens=itens, total=sum(i["valor"] for i in itens))


@app.route('/carrinho/adicionar/<int:ferramenta_id>', methods=['POST'])
def carrinho_adicionar(ferramenta_id):
    """
    Adicionar ao Carrinho
    Coloca uma ferramenta no carrinho (compra ou aluguel, conforme o produto).
    ---
    tags:
      - Serviços e Pedidos (Cliente)
    parameters:
      - name: ferramenta_id
        in: path
        type: integer
      - name: dias_aluguel
        in: formData
        type: integer
    responses:
      302:
        description: Redireciona para o carrinho.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    item = ToolModel.get_by_id(ferramenta_id)
    if not item:
        flash("Ferramenta não encontrada.", "danger")
        return redirect(url_for('loja_page'))

    dias = None
    if item["tipo"].lower() == 'alugar':
        # Quantidade de dias: entre 1 e 30. Se vier algo inválido, considera 1 dia.
        try:
            dias = max(1, min(30, int(request.form.get('dias_aluguel', 1))))
        except ValueError:
            dias = 1

    # Botão "Comprar agora" / "Alugar agora": registra só este item, sem mexer no carrinho
    if request.form.get('agora'):
        user_id = session.get('user_code')
        valor = round(item["preco"] * (dias or 1), 2)
        if dias:
            sucesso, mensagem = ServiceModel.create_rental(user_id, ferramenta_id, dias, valor)
        else:
            sucesso, mensagem = ServiceModel.create_purchase(user_id, ferramenta_id, valor)
        flash(mensagem, "success" if sucesso else "danger")
        return redirect(url_for('perfil_page'))

    carrinho = session.get('carrinho', [])
    if len(carrinho) >= 20:
        flash("O carrinho aceita até 20 itens. Finalize o pedido para adicionar mais.", "danger")
    else:
        carrinho.append({"id": ferramenta_id, "dias": dias})
        session['carrinho'] = carrinho
        flash(f"{item['nome']} foi para o carrinho.", "success")
    return redirect(url_for('carrinho_page'))


@app.route('/carrinho/remover/<int:posicao>', methods=['POST'])
def carrinho_remover(posicao):
    """
    Remover do Carrinho
    Tira um item do carrinho pela posição dele na lista.
    ---
    tags:
      - Serviços e Pedidos (Cliente)
    parameters:
      - name: posicao
        in: path
        type: integer
    responses:
      302:
        description: Redireciona para o carrinho.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    carrinho = session.get('carrinho', [])
    if posicao < len(carrinho):
        carrinho.pop(posicao)
        session['carrinho'] = carrinho
    return redirect(url_for('carrinho_page'))


@app.route('/carrinho/finalizar', methods=['POST'])
def carrinho_finalizar():
    """
    Finalizar Pedido
    Registra a compra ou o aluguel de cada item do carrinho e dá baixa no estoque.
    ---
    tags:
      - Serviços e Pedidos (Cliente)
    responses:
      302:
        description: Vai para o perfil, ou volta ao carrinho se algum item falhar.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    itens = itens_do_carrinho()

    # Cada item é registrado separado. O que falhar (ex.: esgotou) continua no carrinho.
    restantes = []
    for item in itens:
        if "servico" in item:
            sucesso, mensagem = ServiceModel.pagar_manutencao(item["servico"], user_id)
        elif item["dias"]:
            sucesso, mensagem = ServiceModel.create_rental(
                user_id, item["id"], item["dias"], item["valor"])
        else:
            sucesso, mensagem = ServiceModel.create_purchase(
                user_id, item["id"], item["valor"])
        if not sucesso:
            restantes.append(item["entrada"])
            flash(f"{item['nome']}: {mensagem}", "danger")
    session['carrinho'] = restantes

    registrados = len(itens) - len(restantes)
    if registrados:
        flash(f"Pedido finalizado: {registrados} item(ns) registrado(s).", "success")
    return redirect(url_for('carrinho_page' if restantes else 'perfil_page'))


# === 12. PAINEL COLABORADOR ===
@app.route('/colaborador/painel')
def painel_colaborador():
    """
    Painel de Serviços
    Exibe solicitações abertas.
    ---
    tags:
      - Gestão / Colaborador
    responses:
      200:
        description: Traz lista de serviços pendentes.
    """
    servicos_pendentes = ColaboradorModel.get_servicos_pendentes()
    return render_template('painel_colaborador.html', servicos=servicos_pendentes,
                           alugueis=ColaboradorModel.get_alugueis_em_aberto(),
                           respondidos=ColaboradorModel.get_orcamentos_respondidos(),
                           reprovados=ColaboradorModel.get_orcamentos_reprovados(),
                           prontos=ColaboradorModel.get_prontos_para_retirada())


@app.route('/colaborador/devolucao/<int:id_servico>', methods=['POST'])
def registrar_devolucao(id_servico):
    """
    Registrar Devolução
    Marca o aluguel como devolvido e devolve a unidade ao estoque.
    ---
    tags:
      - Gestão / Colaborador
    parameters:
      - name: id_servico
        in: path
        type: integer
    responses:
      302:
        description: Redireciona.
    """
    sucesso, mensagem = ColaboradorModel.registrar_devolucao(id_servico)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for('painel_colaborador'))


# === 13. ATUALIZAR ORÇAMENTO ===
@app.route('/colaborador/orcamento/<int:id_servico>', methods=['POST'])
def atualizar_orcamento(id_servico):
    """
    Definir Preço (Orçamento)
    O colaborador anexa a foto do dano e define o valor total do conserto.
    ---
    tags:
      - Gestão / Colaborador
    parameters:
      - name: id_servico
        in: path
        type: integer
      - name: valor_servico
        in: formData
        type: number
      - name: status_servico
        in: formData
        type: string
      - name: detalhes_dano
        in: formData
        type: string
      - name: imagem_dano
        in: formData
        type: file
    responses:
      302:
        description: Redireciona.
    """
    valor = request.form.get('valor_servico')
    status = request.form.get('status_servico')
    detalhes_dano = request.form.get('detalhes_dano')
    caminho_relativo = salvar_imagem(request.files.get('imagem_dano'), f"manutencao_dano_{id_servico}")
    if caminho_relativo is False:
        flash("Envie a foto em PNG, JPG ou WEBP.", "danger")
        return redirect(url_for('painel_colaborador'))
    sucesso, mensagem = ColaboradorModel.atualizar_orcamento(
        id_servico, valor, status, caminho_relativo, detalhes_dano
    )
    if not sucesso:
        apagar_imagem(caminho_relativo)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for('painel_colaborador'))


@app.route('/colaborador/servico/<int:id_servico>/fechar', methods=['POST'])
def fechar_servico(id_servico):
    """
    Fechar Manutenção
    Depois da resposta do cliente: orçamento aprovado vira "Concluído", reprovado vira "Encerrado".
    ---
    tags:
      - Gestão / Colaborador
    parameters:
      - name: id_servico
        in: path
        type: integer
    responses:
      302:
        description: Redireciona.
    """
    sucesso, mensagem = ColaboradorModel.fechar_servico(id_servico)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for('painel_colaborador'))


@app.route('/colaborador/servico/<int:id_servico>/entregar', methods=['POST'])
def entregar_servico(id_servico):
    """
    Entregar Equipamento
    Registra que o cliente retirou o equipamento (e pagou, se o pagamento era na retirada).
    ---
    tags:
      - Gestão / Colaborador
    parameters:
      - name: id_servico
        in: path
        type: integer
    responses:
      302:
        description: Redireciona.
    """
    sucesso, mensagem = ColaboradorModel.entregar_servico(id_servico)
    flash(mensagem, "success" if sucesso else "danger")
    return redirect(url_for('painel_colaborador'))


# === 14. CLIENTE RESPONDE ORÇAMENTO ===
@app.route('/cliente/orcamento/<int:id_servico>/<resposta>', methods=['POST'])
def responder_orcamento(id_servico, resposta):
    """
    Aprovar/Reprovar Orçamento
    Cliente aceita ou recusa o orçamento feito pelo colaborador.
    ---
    tags:
      - Conta do Cliente
    parameters:
      - name: id_servico
        in: path
        type: integer
      - name: resposta
        in: path
        type: string
    responses:
      302:
        description: Redireciona.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    pagamento = None
    if resposta == 'Aprovado':
        # Antes de aprovar, o cliente escolhe como vai pagar (tela escolher_pagamento)
        pagamento = {'agora': PAGAMENTO_PENDENTE, 'retirada': PAGAMENTO_RETIRADA}.get(request.form.get('pagamento'))
        if not pagamento:
            return redirect(url_for('escolher_pagamento', id_servico=id_servico))

    sucesso, mensagem = ServiceModel.responder_orcamento(
        id_servico, user_id, resposta, pagamento)
    flash(mensagem, "success" if sucesso else "danger")
    if sucesso and pagamento == PAGAMENTO_PENDENTE:
        por_servico_no_carrinho(id_servico)
        return redirect(url_for('carrinho_page'))
    return redirect(url_for('perfil_page'))


@app.route('/cliente/orcamento/<int:id_servico>/pagamento')
def escolher_pagamento(id_servico):
    """
    Escolher o Pagamento
    Pergunta ao cliente se ele paga o orçamento agora (pelo carrinho) ou na retirada do equipamento.
    ---
    tags:
      - Conta do Cliente
    parameters:
      - name: id_servico
        in: path
        type: integer
    responses:
      200:
        description: HTML com as duas opções de pagamento.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    orcamento = ServiceModel.get_orcamento(id_servico, session.get('user_code'))
    if not orcamento or orcamento["status"] != 'Aguardando Aprovação':
        flash("Esse orçamento não está aguardando a sua resposta.", "danger")
        return redirect(url_for('perfil_page'))
    return render_template('pagamento.html', orcamento=orcamento)


@app.route('/carrinho/pagar-servico/<int:id_servico>', methods=['POST'])
def carrinho_pagar_servico(id_servico):
    """
    Pagar Manutenção pelo Carrinho
    Coloca no carrinho o pagamento de uma manutenção aprovada que ficou pendente.
    ---
    tags:
      - Conta do Cliente
    parameters:
      - name: id_servico
        in: path
        type: integer
    responses:
      302:
        description: Redireciona para o carrinho.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    orcamento = ServiceModel.get_orcamento(id_servico, session.get('user_code'))
    if not orcamento or orcamento["pagamento"] != PAGAMENTO_PENDENTE:
        flash("Esse serviço não está aguardando pagamento.", "danger")
        return redirect(url_for('perfil_page'))
    por_servico_no_carrinho(id_servico)
    return redirect(url_for('carrinho_page'))


# === 15. GERENCIAR FERRAMENTAS ===
@app.route('/colaborador/ferramentas', methods=['GET', 'POST'])
def gerenciar_ferramentas():
    """
    Gerenciar Catálogo
    Lista e permite adicionar novas ferramentas ao catálogo.
    ---
    tags:
      - Gestão / Colaborador
    parameters:
      - name: marca
        in: formData
        type: string
      - name: modelo
        in: formData
        type: string
      - name: descricao
        in: formData
        type: string
      - name: tipo_ferramenta
        in: formData
        type: integer
    responses:
      200:
        description: Retorna painel.
    """
    if request.method == 'POST':
        marca = request.form.get('marca')
        modelo = request.form.get('modelo')
        descricao = request.form.get('descricao')
        id_tipo = request.form.get('tipo_ferramenta')
        imagem = salvar_imagem(request.files.get('imagem'), "ferramenta")
        if imagem is False:
            flash("Envie a foto em PNG, JPG ou WEBP.", "danger")
            return redirect(url_for('gerenciar_ferramentas'))
        sucesso, mensagem = ToolModel.create(
            marca, modelo, descricao, id_tipo,
            request.form.get('preco'), request.form.get('tipo_oferta'), imagem)
        if not sucesso:
            apagar_imagem(imagem)
        if sucesso:
            flash(mensagem, "success")
        else:
            flash(mensagem, "danger")
        return redirect(url_for('gerenciar_ferramentas'))
    tipos = ToolModel.get_tipos()
    todas_ferramentas = ToolModel.get_all()
    filiais = AdminModel.get_filiais()
    return render_template('painel_ferramentas.html', tipos=tipos, ferramentas=todas_ferramentas, filiais=filiais)


# === 17. CAIXA ===
@app.route('/colaborador/financeiro')
def relatorio_caixa():
    """
    Relatório Financeiro
    Calcula lucro total somando todos os serviços concluídos.
    ---
    tags:
      - Gestão / Colaborador
    responses:
      200:
        description: Relatório de caixa gerado.
    """
    dados_caixa = ColaboradorModel.get_relatorio_caixa()
    return render_template('caixa.html', caixa=dados_caixa)


# === 18. PERFIS ===
@app.route('/admin/perfis', methods=['GET', 'POST'])
def admin_perfis():
    """
    Gestão de Perfis
    Cadastra níveis de permissão.
    ---
    tags:
      - Administração Base
    responses:
      200:
        description: OK.
    """
    if request.method == 'POST':
        perfil = request.form.get('perfil')
        descricao = request.form.get('descricao')
        sucesso, msg = AdminModel.create_perfil(perfil, descricao)
        flash(msg, "success" if sucesso else "danger")
        return redirect(url_for('admin_perfis'))
    perfis = AdminModel.get_perfis()
    return render_template('admin_perfis.html', perfis=perfis, usuarios=UserAccountModel.listar())


@app.route('/admin/usuarios/<int:id_usuario>/perfil', methods=['POST'])
def admin_mudar_perfil(id_usuario):
    """
    Trocar o Perfil de um Usuário
    Só o Administrador chega aqui (rota /admin), e nunca troca o próprio perfil (para não ficar sem administrador).
    ---
    tags:
      - Administração Base
    parameters:
      - name: id_usuario
        in: path
        type: integer
      - name: id_perfil
        in: formData
        type: integer
    responses:
      302:
        description: Volta para a tela de perfis.
    """
    usuario = next((u for u in UserAccountModel.listar() if u["id"] == id_usuario), None)
    if not usuario:
        flash("Usuário não encontrado.", "danger")
    elif usuario["usuario"] == session.get('user_name'):
        flash("Você não pode trocar o seu próprio perfil.", "danger")
    elif UserAccountModel.mudar_perfil(id_usuario, request.form.get('id_perfil')):
        flash(f"Perfil de {usuario['usuario']} atualizado. Vale na próxima página que ele abrir.", "success")
    else:
        flash("Não foi possível trocar o perfil.", "danger")
    return redirect(url_for('admin_perfis'))


# === 19. FILIAIS ===
@app.route('/admin/filiais', methods=['GET', 'POST'])
def admin_filiais():
    """
    Gestão de Filiais
    Cadastra novas lojas físicas.
    ---
    tags:
      - Administração Base
    responses:
      200:
        description: OK.
    """
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
@app.route('/colaborador/unidades', methods=['POST'])
def cadastrar_unidade():
    """
    Cadastro de Unidade (Física)
    Vincula série de ferramenta ao estoque da filial. Colaborador e Administrador podem lançar.
    ---
    tags:
      - Gestão / Colaborador
    responses:
      302:
        description: OK.
    """
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
    """
    Painel com Gráficos
    Exibe faturamento e quantidade de vendas, aluguéis e manutenções por mês.
    ---
    tags:
      - Gestão / Colaborador
    responses:
      200:
        description: HTML do painel com gráficos.
    """
    dados = PainelModel.get_resumo_mensal()
    return render_template('painel_graficos.html', dados=dados)


if __name__ == "__main__":
    app.run()
