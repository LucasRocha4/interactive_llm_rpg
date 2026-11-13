# LLM Interactive RPG

## Configuração

Crie o arquivo `.env` na raiz do projeto a partir do exemplo:

```bash
cp .env.example .env
```

Gere uma chave secreta com `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` e coloque o resultado no `.env` como valor de `DJANGO_SECRET_KEY`. Não compartilhe nem envie esse arquivo para o Git.

## Executar localmente

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python llm_interactive_rpg/manage.py runserver
```

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

As configurações atuais são para desenvolvimento e não são adequadas para produção.
