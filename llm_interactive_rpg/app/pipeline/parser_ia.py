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

from .modelos_gemini import MODELO_PARSER_PADRAO, gerar_com_fallback
from .schemas import IntentJogador


LOGGER = logging.getLogger("rpg.interpreter")
REGRAS_ROOT = Path(__file__).resolve().parents[2] / "app" / "regras"


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
    with (REGRAS_ROOT / "tabela_itens.json").open(encoding="utf-8") as arquivo:
        categorias_itens = list(json.load(arquivo))
    return {
        "inimigos": [
            {"id": "rato_01", "nome": "Rato Selvagem", "tipo": "inimigo", "defesa": 10, "protecao": 0, "coracoes": {"atual": 4, "maximo": 4}, "nivel": 1, "atributos": {"pulo": 1, "acaso": 1}},
            {"id": "cobra_01", "nome": "Cobra-d'água", "tipo": "inimigo", "defesa": 12, "protecao": 1, "coracoes": {"atual": 5, "maximo": 5}, "nivel": 1, "atributos": {"pulo": 2, "acaso": 1}},
        ],
        "npcs": (
            [] if personagem.get("id") == "bongo_chule"
            else [{"id": "bongo", "nome": "Bongo Chulé", "tipo": "npc"}]
        ),
        "locais": [
            {"id": "clareira", "nome": "Clareira"},
            {"id": "rio", "nome": "Rio"},
        ],
        "objetos": [
            {"id": "pedra_01", "nome": "Pedra"},
            {"id": "barril_01", "nome": "Barril"},
        ],
        "acoes_validas": ids["acoes"] + ["levantar", "recolher_pedras", "dormir", "encerrar_cena", "equipar"],
        "tecnicas_validas": ids["tecnicas"],
        "equipamentos_validos": ids["equipamentos"],
        "categorias_itens": categorias_itens,
        "objetivo": "derrotar:rato_01",
        "fatos": [],
        "abertura_transicao": False,
    }


def interpretar_acao(
    texto: str,
    personagem: dict[str, Any],
    cena: dict[str, Any] | None = None,
    *,
    cliente: Any | None = None,
) -> IntentJogador:
    project_root = Path(__file__).resolve().parents[3]
    load_dotenv(project_root / ".env")
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY nao configurada no ambiente.")

    cena = cena if cena is not None else criar_cena_atual(personagem)
    system_instruction = (
        "Voce interpreta a acao de um jogador em portugues. "
        "Use somente os IDs presentes em cena_atual. "
        "Nao invente IDs, nomes, tecnicas ou equipamentos. "
        "Se faltar informacao critica, preencha perguntas_pendentes e nao execute. "
        "Para testes sem dificuldade fixa, classifique dificuldade como facil, media, dificil ou absurda. "
        "Deixe dificuldade nula para acao trivial e ataques contra inimigos. "
        "Nunca escolha numeros de dificuldade, role dados, calcule dano ou altere o estado. "
        "Use levantar para tentar levantar, recolher_pedras para recolher uma pedra e dormir para descansar. "
        "Para arremessar um objeto da cena, use objeto_id para esse objeto e alvo.id para o alvo. "
        "Use equipar para transferir um equipamento do inventario; para Bolso Misterioso, preencha categoria_item com uma categoria disponivel. "
        "Use encerrar_cena quando o jogador escolher sair ou transicionar apos cumprir o objetivo; nao afirme que o objetivo foi cumprido. "
        "Retorne exclusivamente o IntentJogador definido pelo response_schema.\n"
        f"cena_atual={json.dumps({**cena, 'personagem': personagem}, ensure_ascii=False)}"
    )

    client = cliente if cliente is not None else genai.Client(api_key=api_key)
    config = types.GenerateContentConfig(
        temperature=0.1,
        system_instruction=system_instruction,
        response_mime_type="application/json",
        response_schema=IntentJogador,
    )
    response = gerar_com_fallback(
        client,
        os.getenv("GEMINI_PARSER_MODEL", MODELO_PARSER_PADRAO),
        lambda modelo: client.models.generate_content(
            model=modelo,
            contents=texto,
            config=config,
        ),
        priorizar_economia=True,
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
