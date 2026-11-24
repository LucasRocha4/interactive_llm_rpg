# LLM Interactive RPG

## Configuração

Crie o arquivo `.env` na raiz do projeto a partir do exemplo:

```bash
cp .env.example .env
```

Gere uma chave secreta com `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` e coloque o resultado no `.env` como valor de `DJANGO_SECRET_KEY`. Não compartilhe nem envie esse arquivo para o Git.

Obtenha uma chave da Gemini API e configure `GEMINI_API_KEY` no mesmo arquivo. Opcionalmente, use `GEMINI_NARRATOR_MODEL` para escolher o modelo da segunda LLM; se omitida, a variável usa `gemini-3.5-flash-lite`.

## Executar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python llm_interactive_rpg/manage.py runserver
```

Para testar o pipeline atual no terminal:

```bash
python main.py
```

O terminal mantém a ficha e a cena simuladas em memória durante a sessão. A primeira
etapa Gemini interpreta a intenção e classifica dificuldades; o motor em Python aplica
regras, rola os dados e atualiza personagem e alvos. Uma segunda etapa Gemini recebe
somente o resultado final do motor e o transforma em uma narração curta, sem permissão
para recalcular ou alterar o estado. Configure `GEMINI_API_KEY` para usar o terminal.
Se a narração falhar, a chamada é repetida uma vez e depois o terminal usa um fallback
baseado nos fatos mecânicos. A ficha e os inimigos de exemplo são apenas dados de demonstração.
Por padrão, a ficha de teste selecionada é `bongo_chule`, carregada de
`llm_interactive_rpg/app/regras/exemplos_de_ficha.json` ao iniciar. Os
corações, a infecção inicial e as técnicas disponíveis são inicializados com
base nas regras; as alterações durante a sessão não são gravadas no arquivo.

As regras oficiais ficam em `llm_interactive_rpg/app/regras/`. O inventário
usa um mapa de IDs para quantidades, separado da lista de equipamentos. Ações
incompletas são interrompidas sem consumir recursos. Para levantar quando Caído,
solicite explicitamente levantar; ataques e movimentos são bloqueados. O objetivo
da cena de demonstração é derrotar o rato, e uma transição solicitada depois
disso encerra a cena. Dormir avança o dia apenas sem evento pendente.

Execute os testes sem acesso à API Gemini e valide os dados:

```bash
python -m unittest discover -s tests -v
python llm_interactive_rpg/app/regras/validar.py
```

Consulte [ESTADO_ATUAL.md](ESTADO_ATUAL.md) para os contratos e limites atuais.

## Executar com Docker

```bash
docker build -t llm-interactive-rpg .
docker run --rm --env-file .env -p 8000:8000 llm-interactive-rpg
```

Ou com Docker Compose:

```bash
docker compose up --build
```

A aplicação fica disponível em http://localhost:8000.

Para testar o fluxo de leitura no terminal dentro do mesmo ambiente:

```bash
docker compose run --rm web python main.py
```

As configurações atuais são para desenvolvimento e não são adequadas para produção.
