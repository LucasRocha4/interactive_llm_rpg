# Estado atual do projeto

## O que foi implementado

O pipeline de teste funciona no terminal:

1. O jogador informa uma ação em português.
2. O Gemini interpreta a intenção, os IDs da cena e, quando necessário, a
   dificuldade qualitativa: `facil`, `media`, `dificil` ou `absurda`.
3. A bridge converte a intenção em `PedidoMotor`. Perguntas pendentes impedem a
   execução até que a ação seja esclarecida.
4. O motor Python consulta as regras, executa rolagens e aplica as alterações.
5. O terminal mostra o resultado estruturado, o personagem e a cena.

O Gemini não escolhe dificuldades numéricas, não rola dados e não calcula dano.
O motor aceita um gerador aleatório injetável para testes reproduzíveis. Os
arquivos oficiais de regras ficam em `llm_interactive_rpg/app/regras/`.

### Ficha e cena de teste

- A ficha padrão é **Bongo "Chulé"**, de ID `bongo_chule`, carregada de
  `llm_interactive_rpg/app/regras/exemplos_de_ficha.json`.
- A ficha começa com 6 corações, infecção 0, machado de pedra e a técnica
  Bater no Peito. A cena simulada contém um rato e uma cobra.
- Personagem e cena são mantidos em memória durante a sessão. Ao reiniciar,
  voltam ao estado inicial; a ficha de origem não é alterada.
- O inventário é um mapa de quantidades, separado da lista de equipamentos.
  Informações necessárias ausentes interrompem a ação com esclarecimento.

### Motor de regras

- Dificuldades da tabela: Fácil 8, Média 12, Difícil 16 e Absurda 20.
- Testes usam `d20 + atributo`; vantagem e desvantagem se cancelam. Um 20
  natural garante sucesso e um 1 natural é uma mancada.
- Ataques usam a Defesa do alvo. O dano é fixo, pode ser dobrado por crítico e
  é reduzido pela proteção sem ficar negativo. Estilingues consomem pedras;
  recolher uma pedra exige Manha contra Fácil.
- Com 0 corações, o personagem fica Caído. Pode tentar levantar, usar banana
  curativa ou ativar Cura Dramática quando disponível; outras ações são
  bloqueadas. Três falhas ao levantar causam morte. Infecção 5 causa morte e
  zumbificação.
- As ações e técnicas dos JSONs possuem tratamento no motor, incluindo custos,
  efeitos e limites aplicáveis; ações que exigem contexto ausente solicitam
  esclarecimento.
- Turnos, efeitos e recargas avançam com ações executadas. O encerramento da
  cena depende do objetivo e de uma abertura de transição; dormir pode avançar
  o dia, desde que não haja evento pendente.

## Como testar localmente

Na raiz do projeto, crie e ative o ambiente virtual se necessário:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

### Testes automáticos, sem Gemini

```bash
python -m unittest discover -s tests -v
python llm_interactive_rpg/app/regras/validar.py
```

O primeiro comando deve terminar com `OK`; o segundo, com
`OK: validação concluída`. Para executar somente os testes da ficha padrão:

```bash
python -m unittest discover -s tests -p 'test_ficha_padrao.py' -v
```

### Teste interativo com Gemini

Se ainda não existir, crie `.env` a partir do exemplo, sem sobrescrever um
arquivo já configurado:

```bash
cp -n .env.example .env
```

Edite `.env` e preencha `GEMINI_API_KEY`. Para usar também o servidor Django,
preencha `DJANGO_SECRET_KEY` com uma chave própria. Não compartilhe o arquivo.
Execute:

```bash
python main.py
```

Confirme a mensagem de seleção da ficha `bongo_chule`. No prompt `Jogador>`,
experimente:

```text
Vou recolher uma pedra do chão.
Ataco o rato selvagem com meu machado de pedra.
sair
```

Confira `status`, `rolagem`, `sucesso`, `dano_final`, `Personagem` e `Cena` na
saída. A interpretação pode solicitar esclarecimentos e o resultado do dado é
aleatório. Uma chamada real ao Gemini requer acesso à API e uma chave válida;
os testes automáticos usam resposta simulada.

## Como testar com Docker

O Dockerfile já inclui dependências, código e regras. Com `.env` configurado,
construa a imagem e execute os testes:

```bash
docker compose build
docker compose run --rm --no-deps web python -m unittest discover -s tests -v
docker compose run --rm --no-deps web python llm_interactive_rpg/app/regras/validar.py
```

Para executar o pipeline interativo:

```bash
docker compose run --rm --no-deps web python main.py
```

O comando padrão `docker compose up --build` inicia o servidor Django em
`http://localhost:8000`; o jogo de teste é o comando interativo acima, não uma
interface web. A configuração Docker é voltada ao desenvolvimento.

## Limitações atuais

Não há persistência da partida entre execuções, simulação autônoma de inimigos
nem geração automática de próximas cenas. A cena e os inimigos são exemplos;
algumas ações dependem de informações adicionais no contexto.
