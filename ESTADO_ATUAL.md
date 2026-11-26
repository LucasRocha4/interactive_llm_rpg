# Estado atual do projeto

O projeto é um RPG para jogar pelo terminal, com o motor de regras em Python e
interpretação/narração pelo Gemini. O Django guarda campanhas, personagens,
NPCs e itens. As regras de atributos, pelagens, ofícios, defeitos e equipamentos
ficam nos JSONs de `llm_interactive_rpg/app/regras/`.

## Preparar o ambiente

Na raiz do repositório, instale as dependências no ambiente virtual:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Configure o arquivo `.env` na raiz com `DJANGO_SECRET_KEY` e `GEMINI_API_KEY`.
`DATABASE_URL` pode ficar como `sqlite:///db.sqlite3`, que usa o SQLite local.
Não compartilhe nem faça commit do `.env`.

+## Teste simples: cadastrar e iniciar uma campanha

1. Crie as tabelas e, se ainda não existir, um usuário administrador:

   ```powershell
   .\.venv\Scripts\python.exe llm_interactive_rpg\manage.py migrate
   .\.venv\Scripts\python.exe llm_interactive_rpg\manage.py createsuperuser
   ```

   Ao final de cada `migrate`, o Django garante que exista uma campanha padrão
   com a ficha `bongo_chule`. A ficha é montada a partir de
   `app/regras/exemplos_de_ficha.json`. Se a campanha ou a ficha forem apagadas,
   o próximo `migrate` as cria novamente, sem duplicar os registros existentes.
   O dono técnico da campanha é `campanha_demo_sistema`; o login do painel é a
   conta separada criada por `createsuperuser`.

2. Inicie o painel administrativo:

   ```powershell
   .\.venv\Scripts\python.exe llm_interactive_rpg\manage.py runserver
   ```

3. Abra <http://127.0.0.1:8000/admin/> e veja a campanha
   **Campanha padrão — ficha bongo_chule** e o personagem Bongo "Chulé". Se
   quiser criar a sua própria, use **Campaigns → Add** e depois crie um
   personagem ligado a ela. Para um personagem válido de exemplo, use pelagem
   `marrom`, ofício `lutador`, defeito `cheiro_de_pantano` e equipamento
   `machado_de_pedra`.

4. Abra outro terminal na raiz e inicie o jogo:

   ```powershell
   .\.venv\Scripts\python.exe main.py
   ```
sair
   Confira se aparece `Campanha e ficha carregadas do banco`. Se aparecer
   `usando a ficha de demonstração`, verifique se a campanha está ativa e tem
   personagem. Se houver uma campanha própria ativa com personagem, ela tem
   prioridade sobre a campanha padrão. Se não houver, o programa usa Bongo.

5. Digite uma ação para testar uma rodada, por exemplo:

   ```text
   Ataco o Rato Selvagem com meu machado de pedra.
   ```

   O Gemini interpreta a ação, o motor aplica as regras e o narrador mostra o
   resultado. Digite `sair` para encerrar.

## O que este teste cobre

O programa carrega a campanha, o personagem e os NPCs do banco e usa esses dados
no contexto enviado ao Gemini. A campanha demo serve para testar sem cadastro
manual. O cenário inicial ainda usa elementos fixos do exemplo do jogo. Ainda
não há geração automática de uma jornada completa com missões, cenas e inimigos
próprios a partir da descrição da campanha.

Também existe um teste isolado que cria dados temporários e pede ao Gemini uma
interpretação deles. Com uma `GEMINI_API_KEY` configurada, rode:

```powershell
.\.venv\Scripts\python.exe llm_interactive_rpg\manage.py test app.pipeline.test_gemini_dados_banco --verbosity 2
```

Esse teste chama a API real. Sem a chave, ele é ignorado com uma mensagem
explicativa. Para rodar os testes automáticos do projeto:

```powershell
.\.venv\Scripts\python.exe llm_interactive_rpg\manage.py test tests --verbosity 2
.\.venv\Scripts\python.exe llm_interactive_rpg\app\regras\validar.py
```

Os testes automáticos comuns usam o Gemini simulado; somente o teste isolado
acima chama a API real.
