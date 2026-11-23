from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from dotenv import load_dotenv
from pydantic import ValidationError

from .schemas import IntentJogador


LOGGER = logging.getLogger("rpg.interpreter")
REGRAS_ROOT = Path(__file__).resolve().parents[2] / "config" / "regras"


def carregar_ids_validos() -> dict[str, list[str]]:
    ids: dict[str, list[str]] = {"acoes": [], "tecnicas": [], "equipamentos": []}
    for nome in ids:
        caminho = REGRAS_ROOT / f"{nome}.json"
        with caminho.open(encoding="utf-8") as arquivo:
            registros = json.load(arquivo)
        ids[nome] = [str(registro["id"]) for registro in registros]
    return ids


def criar_cena_atual(personagem: dict[str, Any]) -> dict[str, Any]:
    ids = carregar_ids_validos()
    return {
        "personagem": personagem,
        "inimigos": [
            {"id": "rato_01", "nome": "Rato Selvagem", "tipo": "inimigo"},
            {"id": "cobra_01", "nome": "Cobra-d'água", "tipo": "inimigo"},
        ],
        "npcs": [
            {"id": "bongo", "nome": "Bongo Chulé", "tipo": "npc"},
        ],
        "locais": [
            {"id": "clareira", "nome": "Clareira"},
            {"id": "rio", "nome": "Rio"},
        ],
        "objetos": [
            {"id": "pedra_01", "nome": "Pedra"},
            {"id": "barril_01", "nome": "Barril"},
        ],
        "acoes_validas": ids["acoes"],
        "tecnicas_validas": ids["tecnicas"],
        "equipamentos_validos": ids["equipamentos"],
    }


def interpretar_acao(texto: str, personagem: dict[str, Any]) -> IntentJogador:
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY nao configurada no ambiente.")

    cena = criar_cena_atual(personagem)
    system_instruction = (
        "Voce interpreta a acao de um jogador em portugues. "
        "Use somente os IDs presentes em cena_atual. "
        "Nao invente IDs, nomes, tecnicas ou equipamentos. "
        "Se faltar informacao critica, preencha perguntas_pendentes e nao execute. "
        "Retorne exclusivamente o IntentJogador definido pelo response_schema.\n"
        f"cena_atual={json.dumps(cena, ensure_ascii=False)}"
    )

    client = genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=0.1,
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=IntentJogador,
    )
    response = client.models.generate_content(
        model="gemini-3.5-flash-lite",
        contents=texto,
        config=config,
    )

    try:
        if getattr(response, "parsed", None) is not None:
            if isinstance(response.parsed, IntentJogador):
                intent = response.parsed
            else:
                intent = IntentJogador.model_validate(response.parsed)
        else:
            intent = IntentJogador.model_validate_json(response.text)
    except (ValidationError, json.JSONDecodeError, AttributeError, TypeError) as error:
        LOGGER.error("[STEP 2 - GEMINI PARSER] Falha na validacao Pydantic: %s", error)
        raise

    LOGGER.info(
        "[STEP 2 - GEMINI PARSER] Intent JSON retornado e validado pelo Pydantic: %s",
        json.dumps(intent.model_dump(mode="json"), ensure_ascii=False),
    )
    return intent
