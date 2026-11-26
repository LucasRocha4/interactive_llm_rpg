from __future__ import annotations

import json
import logging
import os
from typing import Any

from google import genai
from google.genai import types

from .modelos_gemini import MODELO_NARRADOR_PADRAO, gerar_com_fallback
from .schemas import ResultadoMotor


LOGGER = logging.getLogger("rpg.narrator")
MODELO_PADRAO = MODELO_NARRADOR_PADRAO


def _contexto_narrativo(resultado: ResultadoMotor) -> dict[str, Any]:
    return {
        "status": resultado.status,
        "sucesso": resultado.sucesso,
        "acao_executada": resultado.acao_executada,
        "rolagens": resultado.rolagens,
        "dano_final": resultado.dano_final,
        "impacto_mecanico": resultado.impacto_mecanico,
        "fatos": resultado.fatos_para_narracao,
        "efeitos": resultado.efeitos,
        "alteracoes_personagem": resultado.alteracoes_personagem,
        "motivo_bloqueio": (
            resultado.motivo_bloqueio.model_dump(mode="json")
            if resultado.motivo_bloqueio is not None
            else None
        ),
    }


def narrativa_fallback(resultado: ResultadoMotor) -> str:
    if resultado.status == "aguardando_esclarecimento":
        perguntas = resultado.efeitos or [
            resultado.motivo_bloqueio.detalhe
            if resultado.motivo_bloqueio is not None
            else "Preciso de mais detalhes para continuar."
        ]
        return "Preciso esclarecer uma coisa antes da ação: " + " ".join(perguntas)

    if resultado.status == "bloqueado_condicao":
        detalhe = (
            resultado.motivo_bloqueio.detalhe
            if resultado.motivo_bloqueio is not None
            else next(iter(resultado.efeitos), "A ação não pôde ser executada.")
        )
        return f"A ação não aconteceu: {detalhe}"

    fatos = resultado.fatos_para_narracao or resultado.efeitos
    if not fatos:
        fatos = ["Ação realizada com sucesso." if resultado.sucesso else "A ação falhou."]
    return " ".join(fatos)


def narrar_resultado(
    texto_jogador: str,
    resultado: ResultadoMotor,
    *,
    cliente: Any | None = None,
) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key and cliente is None:
        LOGGER.warning("Narracao indisponivel: GEMINI_API_KEY nao configurada; usando fallback.")
        return narrativa_fallback(resultado)

    client = cliente
    modelo = os.getenv("GEMINI_NARRATOR_MODEL", MODELO_PADRAO)
    instrucao = (
        "Voce e o narrador de um RPG interativo de aventura leve e comica, em portugues. "
        "Transforme o resultado mecanico recebido em uma resposta curta e envolvente. "
        "O motor de regras e a unica fonte de verdade: nao role dados, nao escolha dificuldades, "
        "nao calcule dano, nao altere atributos, inventario, personagens ou cena. "
        "Nao invente alvos, objetos, consequencias, sucesso ou falha ausentes nos fatos. "
        "Se o status for aguardando_esclarecimento, explique somente a duvida e faca a pergunta necessaria; "
        "nao diga que a acao ocorreu. Se o status for bloqueado_condicao, explique somente o bloqueio. "
        "Para status executado, descreva a acao e suas consequencias exatas. "
        "Retorne apenas a narracao, sem JSON, titulos, listas de campos ou comentarios sobre o motor."
    )
    conteudo = json.dumps(
        {
            "acao_do_jogador": texto_jogador,
            "resultado_do_motor": _contexto_narrativo(resultado),
        },
        ensure_ascii=False,
    )
    config = types.GenerateContentConfig(
        temperature=0.7,
        system_instruction=instrucao,
    )

    if client is None:
        client = genai.Client(api_key=api_key)

    def gerar(modelo_atual: str) -> str:
        resposta = client.models.generate_content(
            model=modelo_atual,
            contents=conteudo,
            config=config,
        )
        texto = getattr(resposta, "text", None)
        if not isinstance(texto, str) or not texto.strip():
            raise RuntimeError("Resposta temporaria vazia da segunda LLM.")
        return texto.strip()

    try:
        return gerar_com_fallback(
            client,
            modelo,
            gerar,
            limite_tentativas=2,
        )
    except Exception as erro:
        LOGGER.error("Falha definitiva na narracao; usando fallback: %s", erro)
        return narrativa_fallback(resultado)
