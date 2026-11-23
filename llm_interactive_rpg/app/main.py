from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv

try:
    from google import genai  # noqa: F401
except ImportError:
    genai = None

from .pipeline.motor_bridge import despachar_para_motor, montar_pedido_motor
from .pipeline.parser_ia import interpretar_acao


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


def personagem_simulado() -> dict[str, object]:
    return {
        "id": "bongo_chule",
        "nome": "Bongo Chulé",
        "nivel": 1,
        "pelagem_id": "marrom",
        "oficio_id": "lutador",
        "defeito_id": "cheiro_de_pantano",
        "atributos": {"garra": 3, "manha": 1, "pulo": 3, "acaso": 1},
        "coracoes": {"atual": 6, "maximo": 6},
        "infeccao": {"atual": 0, "maximo": 5},
        "defesa": 13,
        "equipamentos": ["machado_de_pedra"],
        "tecnicas_disponiveis": ["lutador_n1_bater_no_peito"],
    }


def executar_turno(texto: str, personagem: dict[str, object]) -> None:
    requisicao_id = uuid.uuid4().hex[:12]
    logging.info(
        "[STEP 1 - INPUT] Texto capturado do terminal: %r; requisicao_id gerado: %s",
        texto,
        requisicao_id,
    )

    try:
        intent = interpretar_acao(texto, personagem)
    except Exception as error:
        logging.error("[STEP 2 - GEMINI PARSER] Falha ao interpretar acao: %s", error)
        return

    logging.info(
        "[STEP 3 - VALIDACAO] Verificacao de perguntas_pendentes: %s",
        json.dumps(intent.perguntas_pendentes, ensure_ascii=False),
    )
    if intent.perguntas_pendentes:
        logging.warning(
            "[STEP 3 - VALIDACAO] Ambiguidade encontrada; envio ao motor interrompido."
        )
        for pergunta in intent.perguntas_pendentes:
            print(f"Pergunta: {pergunta}")
        return

    pedido = montar_pedido_motor(intent, requisicao_id)
    despachar_para_motor(pedido, personagem)


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

    personagem = personagem_simulado()
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

        executar_turno(texto, personagem)


if __name__ == "__main__":
    main()