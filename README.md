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

```text
Alexandre Fortunato         Allan Ferreira
Jose Venancio Filho         Jaqueline Moratto
Larissa Vieira              Miguel Correira
Monique Jesus               Ronaldo Alves de Souza
```

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
> Antes de começar a desenvolver, faça as seguintes checagens:
> - Verifique se o MySQL está ativo e rodando em sua máquina
> - Crie o banco `jb_ferramentas` (passo 3 abaixo)
> - Configure o arquivo `.env` com os dados do seu banco (passo 2 abaixo)

## Executar projeto

**1. Instalar as dependências** (dentro do diretório raiz do projeto):
```
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate    # Linux/Mac
pip install -r requirements.txt
```

**2. Configurar o acesso ao banco:** copie o arquivo `.env.example` para `.env` e preencha com o usuário e a senha do **seu** MySQL.
```
copy .env.example .env         # Windows
# cp .env.example .env         # Linux/Mac
```

**3. Criar o banco** (só na primeira vez). O arquivo `database/jb_ferramentas.sql` tem a estrutura das tabelas, sem dados:
```
mysql -u root -p -e "CREATE DATABASE jb_ferramentas"
mysql -u root -p jb_ferramentas < database/jb_ferramentas.sql
cd flaskr
python criar_admin.py          # cria o primeiro administrador (pede usuário e senha)
python cadastrar_exemplos.py   # opcional: ferramentas de exemplo na loja
```

**4. Rodar:**
```
cd flaskr
flask --app main run
```
e logo em seguida clique na _URL_ gerada para acessar o site. A documentação da API (Swagger) fica em `/apidocs`.

## Rodar em produção (nuvem)

O comando `flask run` é só para desenvolver. No servidor, use o Waitress (já está no `requirements.txt`):
```
cd flaskr
waitress-serve --port=8000 main:app
```

## Testes

```
cd flaskr
python -m unittest -v
```
Os testes de integração criam sozinhos um banco separado (`jb_ferramentas_teste`) a partir de `database/jb_ferramentas.sql`. O banco de verdade não é tocado.

## Estrutura inicial de arquivos do projeto (Modelo do Flask)

> [!TIP]
> Dê uma olhada na documentaçao do flask sobre estrutura de projetos: [Estruturando projeto com Flask](https://flask.palletsprojects.com/en/stable/tutorial/layout/).

Na pasta **flaskr** está toda a estrutura do projeto.

- **Pasta model**: Arquivos que contem classes que fazer conexão direta com banco de dados e manejam algumas regras de negócio.
- **Pasta templates**: Arquivos que contém o HTML.
- **Pasta static**: CSS, imagens e scripts JavaScript (ex.: `js/register.js`, com busca de CEP e validações do cadastro).
- **main.py**: Arquivo com todas as rotas (por enquanto). As configurações do banco são lidas do arquivo `.env`.


> [!CAUTION]
> Nunca coloque senhas direto no código. Os dados de conexão ficam apenas no arquivo **.env**, que está no `.gitignore` e não vai para o GitHub.
