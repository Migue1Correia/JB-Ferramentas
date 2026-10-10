"""
Cadastra as ferramentas de exemplo no banco, para a loja não ficar vazia.

Como usar (com a .venv ativada):
    cd flaskr
    python cadastrar_exemplos.py

Pode rodar mais de uma vez: a ferramenta que já existe só tem preço, tipo e foto atualizados.
"""
from main import app
from model.db import db_execute

TIPO_FERRAMENTA = "Furadeiras e Parafusadeiras"

# (marca, modelo, descrição, preço, tipo de oferta, foto). No aluguel, o preço é a diária.
FERRAMENTAS = [
    ("JB Pro", "Parafusadeira e Furadeira a Bateria 20V",
     "Sem fio, com bateria de 20V e mandril de aperto rápido. Boa para montar móveis e furar madeira e metal.",
     459.90, "Comprar", "img/produto2.png"),
    ("Wap", "Parafusadeira e Furadeira 12V",
     "Compacta e leve, com bateria de lítio de 12V. Ideal para pequenos reparos em casa.",
     329.90, "Comprar", "img/produto3.png"),
    ("JB Pro", "Furadeira Parafusadeira 3/8 21V com Kit",
     "Sem fio, 21V, mandril de 10 mm e 2 velocidades (0-350/1300 rpm). Acompanha 2 baterias de lítio, carregador, brocas, bits e maleta.",
     361.00, "Comprar", "img/produto.png"),
    ("JB Pro", "Furadeira de Impacto 750W",
     "Com fio, 750W e empunhadura lateral. Indicada para furar concreto e alvenaria.",
     35.00, "Alugar", "img/produto.png"),
    ("Bosch", "Esmerilhadeira Angular 115 mm 710W",
     "Com fio, 710W e 12.000 rpm, para disco de 115 mm. Tem trava do disco e protetor embutido; acompanha a chave. Pesa 1,8 kg.",
     30.00, "Alugar", "img/produto4.png"),
]

UNIDADES_POR_FERRAMENTA = 3


def buscar_id(arg, *valores):
    """Devolve o id do primeiro registro encontrado, ou None se não existir."""
    res = db_execute(arg, *valores, fetch_type="one")
    return res[1][0] if res[0] and res[1] else None


def executar(arg, *valores):
    """Roda um comando e devolve o resultado (no INSERT, o id criado). Para o script se der erro."""
    res = db_execute(arg, *valores)
    if not res[0]:
        raise SystemExit(f"Erro no banco: {res[1]}")
    return res[1]


def cadastrar():
    # 1. Tipo de ferramenta (a tabela ferramentas exige um tipo)
    id_tipo = buscar_id("SELECT id FROM ferramenta_tipos WHERE tipo=%s;", TIPO_FERRAMENTA)
    if not id_tipo:
        id_tipo = executar("INSERT INTO ferramenta_tipos (tipo) VALUES (%s);", TIPO_FERRAMENTA)
        print(f"Tipo criado: {TIPO_FERRAMENTA}")

    # 2. Filial onde as unidades ficam em estoque: usa a primeira que existir ou cria a Matriz
    id_filial = buscar_id("SELECT id FROM filiais ORDER BY id LIMIT 1;")
    if not id_filial:
        id_filial = executar(
            "INSERT INTO filiais (codigo_filial, nome, endereco) VALUES (%s, %s, %s);",
            "MATRIZ", "Matriz", "Endereço de exemplo")
        print("Filial criada: Matriz")

    # 3. Ferramentas e suas unidades em estoque
    for marca, modelo, descricao, preco, tipo_oferta, imagem in FERRAMENTAS:
        id_ferramenta = buscar_id("SELECT id FROM ferramentas WHERE marca=%s AND modelo=%s;", marca, modelo)
        if id_ferramenta:
            executar("UPDATE ferramentas SET preco=%s, tipo_oferta=%s, imagem=%s WHERE id=%s;",
                     preco, tipo_oferta, imagem, id_ferramenta)
            print(f"Atualizada: {marca} {modelo}")
            continue

        id_ferramenta = executar(
            """INSERT INTO ferramentas (marca, modelo, descricao, id_ferramenta_tipo, preco, tipo_oferta, imagem)
               VALUES (%s, %s, %s, %s, %s, %s, %s);""",
            marca, modelo, descricao, id_tipo, preco, tipo_oferta, imagem)

        for numero in range(1, UNIDADES_POR_FERRAMENTA + 1):
            executar(
                "INSERT INTO unidade_ferramentas (numero_serie, id_ferramenta, id_filial, status) VALUES (%s, %s, %s, 'em_estoque');",
                f"EX-{id_ferramenta}-{numero}", id_ferramenta, id_filial)

        print(f"Cadastrada: {marca} {modelo} ({UNIDADES_POR_FERRAMENTA} unidades em estoque)")


if __name__ == "__main__":
    with app.app_context():
        cadastrar()
