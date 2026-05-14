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
> - Verifique se o banco já está criado
> - Verifique em **main.py** se as informações para acessar o seu banco estão corretos
> - Verifique se já está instalado em seu ambiente python os pacotes **flask**, **flask_mysqldb** e **flask-bcrypt**

## Executar projeto

Dentro do diretório raiz do projeto, execute os seguintes comandos:
```
cd flaskr
flask --app main run
```
e logo em seguida clique na _URL_ gerado para acessar o site.

## Estrutura inicial de arquivos do projeto (Modelo do Flask)

> [!TIP]
> Dê uma olhada na documentaçao do flask sobre estrutura de projetos: [Estruturando projeto com Flask](https://flask.palletsprojects.com/en/stable/tutorial/layout/).

Na pasta **flaskr** está toda a estrutura do projeto.

- **Pasta model**: Arquivos que contem classes que fazer conexão direta com banco de dados e manejam algumas regras de negócio.
- **Pasta templates**: Arquivos que contém o HTML.
- **main.py**: Arquivo com todas as rotas (por enquanto), e configurações para conexão com o banco.


> [!CAUTION]
> Antes de fazer o commit, tome cuidado para não vazar as informações de conexão para o seu banco que estão na pasta **main.py**.
