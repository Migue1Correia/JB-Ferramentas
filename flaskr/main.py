import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from flask_bcrypt import Bcrypt
from werkzeug.utils import secure_filename
from flasgger import Swagger
from model.db import jb_solucoes_db, jb_bcrypt
from model.user_account import UserAccountModel
from model.person import PersonModel
from model.toolmodel import ToolModel
from model.service import ServiceModel
from model.colaborador import ColaboradorModel
from model.admin import AdminModel

app = Flask(__name__)
swagger = Swagger(app)

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Mm@965122613'
app.config['MYSQL_DB'] = 'jb_ferramentas'

app.config['SECRET_KEY'] = 'jb_ferramentas_2026'

UPLOAD_FOLDER = os.path.join(
    app.root_path, 'static', 'uploads', 'equipamentos')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

jb_solucoes_db.init_app(app)
jb_bcrypt = Bcrypt(app)


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
    Exibe uma vitrine com até 3 ferramentas em destaque.
    ---
    tags:
      - Público
    responses:
      200:
        description: HTML da vitrine.
    """
    usuario_logado = session.get("user_name")
    ferramentas_db = ToolModel.get_all(limit=3)

    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            nome_completo = f"{f[1]} {f[2]}"
            lista_ferramentas.append({
                "id": f[0],
                "nome": nome_completo,
                "preco": "150,00",
                "tipo": "Comprar/Alugar"
            })

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

    ferramentas_db = ToolModel.get_all()
    lista_ferramentas = []
    if ferramentas_db:
        for f in ferramentas_db:
            nome_completo = f"{f[1]} {f[2]}"
            lista_ferramentas.append({
                "id": f[0],
                "nome": nome_completo,
                "preco": "150,00",
                "tipo": "Comprar/Alugar"
            })

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
    return render_template('detalhes.html', ferramenta=ferramenta_selecionada)


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
        usuario = request.form.get("usuario")
        senha = request.form.get("senha")

        if UserAccountModel.auth(usuario, senha):
            dados_conta = UserAccountModel.get(usuario)

            if dados_conta and "id_person" in dados_conta:
                session['user_code'] = dados_conta["id_person"]
                session['logged_in'] = True
                session['user_name'] = usuario
                flash("Login realizado com sucesso!", "success")
                return redirect(url_for('ferramentas_page'))

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
        status = "Dados atualizados com sucesso!"

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
        name = request.form.get('nome')
        user_type = request.form.get('tipo')
        code = request.form.get('code')
        address = request.form.get('endereco')
        email = request.form.get('email')
        phone_number = request.form.get('telefone')
        user = request.form.get('usuario')
        password = request.form.get('senha')

        if PersonModel.exist(code, by="code"):
            status = "CPF/CNPJ já cadastrado."
            return render_template('register.html', status=status)

        if not PersonModel.create(name, user_type, code, address, email, phone_number):
            status = "Erro no cadastro."
            return render_template('register.html', status=status)

        person_infos = PersonModel.get(code)
        hashed_password = jb_bcrypt.generate_password_hash(
            password).decode("utf-8")

        if not UserAccountModel.create(user, hashed_password, person_infos["id"], 1, True):
            status = f"Erro na conta."
            return render_template('register.html', status=status)

        status = "Cadastro realizado com sucesso"
        return render_template('register.html', status=status)


# === 8. LOGOUT ===
@app.route('/logout')
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
    """
    Alugar Ferramenta
    Registra o aluguel de uma unidade.
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
      - name: valor_total
        in: formData
        type: number
    responses:
      302:
        description: Retorno do pedido.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    dias = request.form.get('dias_aluguel', 1)
    valor_total = request.form.get('valor_total', 0)
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
    """
    Comprar Ferramenta
    Registra a venda e dá baixa no estoque.
    ---
    tags:
      - Serviços e Pedidos (Cliente)
    parameters:
      - name: ferramenta_id
        in: path
        type: integer
      - name: valor_total
        in: formData
        type: number
    responses:
      302:
        description: Retorno do pedido.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    user_id = session.get('user_code')
    valor_total = request.form.get('valor_total', 0)
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
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    servicos_pendentes = ColaboradorModel.get_servicos_pendentes()
    return render_template('painel_colaborador.html', servicos=servicos_pendentes)


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
    return render_template('painel_ferramentas.html', tipos=tipos, ferramentas=todas_ferramentas)


# === 16. ADICIONAR PEÇAS ===
@app.route('/colaborador/orcamento/<int:id_servico>/peca', methods=['POST'])
def adicionar_peca_orcamento(id_servico):
    """
    Adicionar Peças na Manutenção
    Vincula peças gastas ao conserto, dando baixa no estoque de peças.
    ---
    tags:
      - Gestão / Colaborador
    parameters:
      - name: id_servico
        in: path
        type: integer
      - name: id_estoque_peca
        in: formData
        type: integer
      - name: quantidade
        in: formData
        type: integer
    responses:
      302:
        description: Redireciona.
    """
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
    if not session.get('logged_in'):
        return redirect(url_for('login'))
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
    """
    Cadastro de Unidade (Física)
    Vincula série de ferramenta ao estoque da filial.
    ---
    tags:
      - Administração Base
    responses:
      302:
        description: OK.
    """
    if not session.get('logged_in'):
        return redirect(url_for('login'))
    numero_serie = request.form.get('numero_serie')
    id_ferramenta = request.form.get('id_ferramenta')
    id_filial = request.form.get('id_filial')
    sucesso, msg = AdminModel.create_unidade_ferramenta(
        numero_serie, id_ferramenta, id_filial)
    flash(msg, "success" if sucesso else "danger")
    return redirect(url_for('gerenciar_ferramentas'))


if __name__ == "__main__":
    app.run(debug=True)
