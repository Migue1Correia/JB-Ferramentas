<div align="center">
  <img width="150" height="70" alt="Image" src="https://github.com/user-attachments/assets/52cf25e1-af6a-46cb-b785-67593763611a" />
  <h1>JB-Ferramentas</h1>
</div>

<div align="center">
  <font style="color: orange; font-weight: bold; font-size: 20px;">
  </u>Gestão comércio & manutenção de ferramentas.
  </font>
</div>

Projeto universitario ( Univesp ) <br>
Orientadora: Crislandy Barreiro <br>
Participantes: <br>

<pre>
Alexandre Fortunato         Allan Ferreira
Jose Venancio Filho         Jaqueline Moratto
Larissa  Vieira             Miguel Correira
Monique Jesus               Ronaldo Alves de Souza
</pre>

## 🛠️ Tecnologias e Conceitos

![UML](https://img.shields.io/badge/UML-2566E8?style=for-the-badge&logo=uml&logoColor=white)
![Git](https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![Design Thinking](https://img.shields.io/badge/Design_Thinking-FF5722?style=for-the-badge)
![CSS](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-4479A1?style=for-the-badge&logo=mysql&logoColor=white)
![Figma](https://img.shields.io/badge/Figma-F24E1E?style=for-the-badge&logo=figma&logoColor=white)
![UX/UI](https://img.shields.io/badge/UX%2FUI-FF69B4?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)


> [!IMPORTANT]
**Orientações** <br>
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
