# Estado atual do projeto

Este projeto está em uma etapa intermediária: já existe um pipeline de terminal que lê uma ação em português, usa o Gemini para transformá-la em um `IntentJogador` validado e monta um `PedidoMotor` para o motor de regras.

O motor de regras ainda não está conectado à implementação. Até esse módulo existir, o payload válido é escrito em `llm_interactive_rpg/ultimo_pedido_motor.json` e o terminal mostra que o despacho ficou fora da fila.

## Fluxo implementado

O ponto de entrada é o [main.py](main.py):

1. `main.py` chama `main()` em `llm_interactive_rpg/app/main.py`.
2. O programa carrega o `.env` da raiz.
3. O terminal solicita texto com `Jogador>`.
4. `interpretar_acao()` envia o texto e a cena atual para o Gemini.
5. A resposta deve seguir o modelo Pydantic `IntentJogador`.
6. Se houver perguntas pendentes, o envio ao motor é interrompido e o terminal pergunta o que falta.
7. Quando não há ambiguidade, `montar_pedido_motor()` cria o contrato `PedidoMotor`.
8. `despachar_para_motor()` tenta encontrar o motor de regras.
9. Enquanto o motor estiver desconectado, o payload é salvo em `llm_interactive_rpg/ultimo_pedido_motor.json`.

O personagem usado neste estágio é simulado em `personagem_simulado()` em `llm_interactive_rpg/app/main.py`. Os inimigos, NPCs, locais e objetos presentes na cena também são dados de exemplo. Não há persistência de ficha nem uma conversa entre comandos.

## Contratos principais

Os contratos estão em `llm_interactive_rpg/app/pipeline/schemas.py`:

- `IntentJogador`: formato estruturado produzido pela IA.
- `PedidoMotor`: formato enxuto que será enviado ao motor.
- `ParametrosMotor`: alvo, equipamento, quantidade, distância e tamanho.
- `TesteMotor`: atributo e vantagem ou desvantagem.

O formato final contém, entre outros campos:

```json
{
  "requisicao_id": "identificador_curto",
  "tipo": "mover",
  "acao_id": null,
  "tecnica_id": null,
  "parametros": {
    "alvo_id": "clareira",
    "equipamento_id": null,
    "quantidade": null,
    "distancia_m": null,
    "tamanho_objeto": null
  },
  "teste": {
    "atributo_id": null,
    "vantagem": false,
    "desvantagem": false
  }
}
```

Os IDs válidos são extraídos dos arquivos JSON em `llm_interactive_rpg/config/regras/`. Isso evita que o Gemini invente ações, técnicas ou equipamentos fora da base atual.

## Pré-configuração necessária

### Opção A: executar localmente

Na raiz do projeto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Copie o modelo de ambiente:

```bash
cp .env.example .env
```

Edite `.env` e configure duas variáveis:

```dotenv
DJANGO_SECRET_KEY=sua-chave-secreta
GEMINI_API_KEY=sua-chave-da-api-gemini
```

Gere uma chave Django, por exemplo:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(50))"
```

Não reutilize uma chave que já foi compartilhada ou publicada. O `.env` está ignorado pelo Git e não deve ser enviado ao repositório.

### Opção B: executar com Docker

Requisitos: Docker e Docker Compose.

Na raiz do projeto, crie o `.env` como descrito acima e execute:

```bash
docker compose up --build
```

Isso inicia o servidor Django em `http://localhost:8000`.

Para usar o pipeline do terminal, em outro terminal execute:

```bash
docker compose run --rm web python main.py
```

Como o compose mantém o repositório montado em `/app`, alterações nos arquivos locais ficam disponíveis no contêiner sem reconstruir a imagem.

## Como testar o `main.py`

Execute:

```bash
python main.py
```

Entrada simples já válida:

```text
Jogador> vou para a clareira
```

A saída esperada inclui, nesta ordem:

1. `[STEP 1 - INPUT]`: texto recebido e ID da requisição.
2. `[STEP 2 - GEMINI PARSER]`: `IntentJogador` retornado e validado.
3. `[STEP 3 - VALIDACAO]`: lista de perguntas pendentes.
4. `[STEP 4 - ADAPTER]`: payload completo do `PedidoMotor`.
5. `[STEP 5 - MOTOR DISPATCH]`: aviso de que o motor está indisponível e caminho da outbox.

Exemplos úteis para testar:

```text
Jogador> vou para a clareira
Jogador> atacar o rato com o machado
Jogador> investigar a pedra
Jogador> sair
```

Se a IA considerar que falta uma informação crítica, ela deve preencher `perguntas_pendentes`. Nesse caso, o programa mostra a pergunta e não envia nem grava um pedido incompleto.

Ao terminar um despacho bem formado sem motor conectado, confira:

```bash
cat llm_interactive_rpg/ultimo_pedido_motor.json
```

No Docker:

```bash
docker compose run --rm web cat llm_interactive_rpg/ultimo_pedido_motor.json
```

## Validação da base de regras

Antes de testar ou alterar os arquivos JSON de regras:

```bash
python llm_interactive_rpg/config/regras/validar.py
```

O comando deve terminar com `OK: validação concluída`. Ele verifica os IDs, referências cruzadas, quantidades e regras estruturais dos dados.

## Situação atual e próximos passos

O que já funciona:

- leitura de texto no terminal;
- configuração da chave Gemini por ambiente;
- criação da cena atual;
- resposta estruturada e validada por Pydantic;
- interrupção segura para informações ambíguas;
- montagem de `PedidoMotor`;
- serialização do payload em JSON.

O que ainda falta:

- implementar ou integrar o módulo real do motor de regras;
- habilitar `MOTOR_DISPONIVEL = True` em `motor_bridge.py` após o módulo existir;
- definir o formato e o tratamento da resposta do motor;
- devolver o resultado do motor ao terminal;
- persistir personagem e estado da partida;
- substituir os dados simulados por entrada real do usuário.
