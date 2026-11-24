from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from copy import deepcopy
from pathlib import Path

from dotenv import load_dotenv

try:
    from google import genai  # noqa: F401
except ImportError:
    genai = None

from .pipeline.motor_bridge import despachar_para_motor, montar_pedido_motor, salvar_na_outbox
from .pipeline.narrador_ia import narrar_resultado
from .pipeline.parser_ia import criar_cena_atual, interpretar_acao
from .motor.regras_engine import REGRAS_ROOT, MotorRegras
from .pipeline.schemas import ResultadoMotor


FICHA_PADRAO_ID = "bongo_chule"


def configurar_logs() -> None:
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    raiz = logging.getLogger()
    raiz.setLevel(logging.INFO)
    raiz.handlers.clear()
    raiz.addHandler(handler)


def personagem_simulado(motor: MotorRegras | None = None) -> dict[str, object]:
    if motor is None:
        motor = MotorRegras()
    with (REGRAS_ROOT / "exemplos_de_ficha.json").open(encoding="utf-8") as arquivo:
        fichas = json.load(arquivo)
    correspondentes = [ficha for ficha in fichas if ficha["id"] == FICHA_PADRAO_ID]
    if len(correspondentes) != 1:
        raise ValueError(f"Esperada uma ficha de exemplo com id {FICHA_PADRAO_ID!r}.")
    ficha = correspondentes[0]
    escolhas = ficha["escolhas"]
    coracoes = motor.regras["coracoes"]["valores"]["iniciais"]
    infeccao = motor.regras["infeccao"]["valores"]
    tecnicas = [
        tecnica["id"]
        for tecnica in motor.tecnicas.values()
        if tecnica["oficio_id"] == escolhas["oficio_id"]
        and tecnica["nivel"] <= escolhas["nivel"]
    ]
    return {
        "id": ficha["id"],
        "nome": ficha["nome"],
        "nivel": escolhas["nivel"],
        "pelagem_id": escolhas["pelagem_id"],
        "oficio_id": escolhas["oficio_id"],
        "defeito_id": escolhas["defeito_id"],
        "atributos": dict(ficha["atributos_calculados"]),
        "coracoes": {"atual": coracoes, "maximo": coracoes},
        "infeccao": {"atual": infeccao["minimo"], "maximo": infeccao["maximo"]},
        "defesa": ficha["defesa"],
        "equipamentos": [escolhas["equipamento_id"]],
        "inventario": {"pedra": 0, "banana_curativa": 0},
        "condicoes": [],
        "turnos_caido": 0,
        "tecnicas_disponiveis": tecnicas,
    }


def executar_turno(
    texto: str,
    personagem: dict[str, object],
    cena: dict[str, object] | None = None,
    motor: MotorRegras | None = None,
) -> ResultadoMotor | None:
    if cena is None:
        cena = criar_cena_atual(personagem)
    if motor is None:
        motor = MotorRegras()
    requisicao_id = uuid.uuid4().hex[:12]
    logging.info(
        "[STEP 1 - INPUT] Texto capturado do terminal: %r; requisicao_id gerado: %s",
        texto,
        requisicao_id,
    )

    try:
        intent = interpretar_acao(texto, personagem, cena)
    except Exception as error:
        logging.error("[STEP 2 - GEMINI PARSER] Falha ao interpretar acao: %s", error)
        return

    logging.info(
        "[STEP 3 - VALIDACAO] Verificacao de perguntas_pendentes: %s",
        json.dumps(intent.perguntas_pendentes, ensure_ascii=False),
    )
    if intent.perguntas_pendentes:
        logging.warning(
            "[STEP 3 - VALIDACAO] Ambiguidade encontrada; motor informado para bloquear sem mutacao."
        )

    pedido = montar_pedido_motor(intent, requisicao_id)
    salvar_na_outbox(pedido)
    personagem_candidato, cena_candidata = deepcopy((personagem, cena))
    resultado = despachar_para_motor(pedido, personagem_candidato, cena_candidata, motor)
    if resultado.sucesso is True:
        personagem.clear()
        personagem.update(personagem_candidato)
        cena.clear()
        cena.update(cena_candidata)
    logging.info(
        "[STEP 5 - NARRADOR] Resultado mecanico recebido: %s",
        json.dumps(resultado.model_dump(mode="json"), ensure_ascii=False),
    )
    print(narrar_resultado(texto, resultado))
    return resultado


def main() -> None:
    project_root = Path(__file__).resolve().parents[2]
    load_dotenv(project_root / ".env")
    configurar_logs()
    logging.info("Pipeline de comandos do RPG iniciado.")

    if genai is None:
        logging.error("Dependencia google-genai nao instalada. Execute: pip install google-genai")
        return
    if not os.getenv("GEMINI_API_KEY"):
        logging.error("GEMINI_API_KEY nao configurada. Defina a variavel de ambiente antes de iniciar.")
        return

    motor = MotorRegras()
    personagem = personagem_simulado(motor)
    logging.info("Ficha de teste selecionada: %s (%s).", personagem["nome"], personagem["id"])
    cena = criar_cena_atual(personagem)
    while True:
        try:
            texto = input("Jogador> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nEncerrando...")
            break

        if not texto:
            continue
        if texto.lower() in {"sair", "exit", "quit"}:
            logging.info("Comando sair recebido. Encerrando limpo.")
            break

        executar_turno(texto, personagem, cena, motor)


if __name__ == "__main__":
    main()