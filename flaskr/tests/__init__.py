"""
Testes automáticos do projeto.

Como rodar (com a .venv ativada):
    cd flaskr
    python -m unittest -v

- test_unidade.py: testa funções sozinhas, sem banco (validação, preço, painel).
- test_integracao.py: testa as telas de verdade, com um banco separado
  (jb_ferramentas_teste) criado sozinho a partir de database/jb_ferramentas.sql.
  O banco de verdade não é tocado.
"""
import os

# Precisa vir antes de qualquer "import main": faz o sistema conectar no banco de teste.
os.environ["MYSQL_DB"] = "jb_ferramentas_teste"
