"""
Cadastra 3 ferramentas de exemplo no banco, para a loja não ficar vazia.

Como usar (com a .venv ativada):
    cd flaskr
    python cadastrar_exemplos.py

Pode rodar mais de uma vez: o que já estiver cadastrado é pulado.
Preço, tipo (comprar/alugar) e foto de cada exemplo ficam em model/toolmodel.py.
"""
from main import app
from model.db import db_execute

TIPO_FERRAMENTA = "Furadeiras e Parafusadeiras"

# (marca, modelo, descrição) - o modelo precisa ser igual ao do CATALOGO_EXEMPLOS em model/toolmodel.py
FERRAMENTAS = [
    ("JB Pro", "Parafusadeira e Furadeira a Bateria 20V",
     "Sem fio, com bateria de 20V e mandril de aperto rápido. Boa para montar móveis e furar madeira e metal."),
    ("Wap", "Parafusadeira e Furadeira 12V",
     "Compacta e leve, com bateria de lítio de 12V. Ideal para pequenos reparos em casa."),
    ("JB Pro", "Furadeira de Impacto 750W",
     "Com fio, 750W e empunhadura lateral. Indicada para furar concreto e alvenaria."),
]

UNIDADES_POR_FERRAMENTA = 3


def buscar_id(arg, *valores):
    """Devolve o id do primeiro registro encontrado, ou None se não existir."""
    res = db_execute(arg, *valores, fetch_type="one")
    return res[1][0] if res[0] and res[1] else None


def inserir(arg, *valores):
    """Faz um INSERT e devolve o id criado. Para o script se der erro."""
    res = db_execute(arg, *valores)
    if not res[0]:
        raise SystemExit(f"Erro no banco: {res[1]}")
    return res[1]


def cadastrar():
    # 1. Tipo de ferramenta (a tabela ferramentas exige um tipo)
    id_tipo = buscar_id("SELECT id FROM ferramenta_tipos WHERE tipo=%s;", TIPO_FERRAMENTA)
    if not id_tipo:
        id_tipo = inserir("INSERT INTO ferramenta_tipos (tipo) VALUES (%s);", TIPO_FERRAMENTA)
        print(f"Tipo criado: {TIPO_FERRAMENTA}")

    # 2. Filial onde as unidades ficam em estoque: usa a primeira que existir ou cria a Matriz
    id_filial = buscar_id("SELECT id FROM filiais ORDER BY id LIMIT 1;")
    if not id_filial:
        id_filial = inserir(
            "INSERT INTO filiais (codigo_filial, nome, endereco) VALUES (%s, %s, %s);",
            "MATRIZ", "Matriz", "Endereço de exemplo")
        print("Filial criada: Matriz")

    # 3. Ferramentas e suas unidades em estoque
    for marca, modelo, descricao in FERRAMENTAS:
        if buscar_id("SELECT id FROM ferramentas WHERE marca=%s AND modelo=%s;", marca, modelo):
            print(f"Já cadastrada: {marca} {modelo}")
            continue

        id_ferramenta = inserir(
            "INSERT INTO ferramentas (marca, modelo, descricao, id_ferramenta_tipo) VALUES (%s, %s, %s, %s);",
            marca, modelo, descricao, id_tipo)

        for numero in range(1, UNIDADES_POR_FERRAMENTA + 1):
            inserir(
                "INSERT INTO unidade_ferramentas (numero_serie, id_ferramenta, id_filial, status) VALUES (%s, %s, %s, 'em_estoque');",
                f"EX-{id_ferramenta}-{numero}", id_ferramenta, id_filial)

        print(f"Cadastrada: {marca} {modelo} ({UNIDADES_POR_FERRAMENTA} unidades em estoque)")


if __name__ == "__main__":
    with app.app_context():
        cadastrar()
