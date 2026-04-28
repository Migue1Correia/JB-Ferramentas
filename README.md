# JB-Ferramentas
Gestão de comercio e manutenção de ferramentas. <br>
Este é um projeto universitario ( PI - Univesp ) <br>
Projeto integrador e conta com os participantes: <br>
Alexandre Fortunato, Allan Ferreira, Jackeline, Jose Venancio Filho <br>
Larissa Vieira, Miguel Correira, Monique Jesus, Ronaldo Alves de Souza <br>

Antes de começar a desenvolver, faça as seguintes checagens:
- Verifique se o MySQL está ativo e rodando em sua máquina
- Verifique se o banco já está criado
- Verifique em **main.py** se as informações para acessar o seu banco estão corretos
- Verifique se já está instalado em seu ambiente python os pacotes **flask** e **flask_mysqldb**

## Como rodar?

Dentro da pasta **flaskr**, no terminal execute o comando:
- flask --app main run

Clique na URL gerado para acessar o site.

## Estrutura inicial de arquivos do projeto (Modelo do Flask)
- [Recomendação do Flask](https://flask.palletsprojects.com/en/stable/tutorial/layout/).

Na pasta **flaskr** está todo o conteudo de nosso projeto. Na pasta **flaskr/templates** estarão todos os HTMLS que o flask consegue enxergar.
Dentro da pasta **flaskr** teremos arquivos python, alguns exemplos são:
- **main.py**: Onde estarão todas as rotas
- **db.py**: Onde estão armazenados a conexão com o banco e a função de execução
- **auth.py**: Onde estão as funções para manipular dados de pessoa/usuario
- **...**: Add novos arquivos python

## db.py - db_execute(arg, *parsing, fetch_type)

Importa a função com o comando: _from db import db_execute_

- **arg**: Comando MySql. Exemplo: _"SELECT * FROM pessoas WHERE nome=%s AND tipo=%s"_, onde %s será substituido pelo parâmetro ***parsing**
- ***parsing**: Usando o exemplo de cima, e supondo que já temos definido as variaveis **nome** e **tipo**: _nome, tipo_
- **fetch_type**: Se a função deve retornar somente o primeiro registro **"one"** ou todos os registros achandos na consulta **"all"**

- **Exemplo completo**: _db_execute("SELECT * FROM pessoas WHERE nome=%s AND tipo=%s", nome, tipo, fetch_type="all")_

## Antes de fazer o commit

- Tome cuidado para não vazar as informações de conexão para o seu banco que estão em **main.py**