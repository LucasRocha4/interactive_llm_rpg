from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable, Iterable
from typing import Any, TypeVar


LOGGER = logging.getLogger("rpg.gemini")
MODELO_PARSER_PADRAO = "gemini-3.5-flash-lite"
MODELO_NARRADOR_PADRAO = "gemini-3.5-flash-lite"
MODELOS_RESERVA = (
    "gemini-3.5-flash",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.5-flash",
)
CACHE_SEGUNDOS = 60.0
_T = TypeVar("_T")
_cache_modelos: tuple[str, ...] = ()
_cache_expira_em = 0.0


def _nome_curto(nome: object) -> str:
    texto = str(nome or "").strip()
    return texto.removeprefix("models/")


def _eh_modelo_texto(nome: str) -> bool:
    nome_minusculo = nome.lower()
    if not nome_minusculo.startswith("gemini-"):
        return False
    return not any(
        termo in nome_minusculo
        for termo in ("image", "preview", "experimental", "exp-", "omni", "banana")
    )


def _ordem_modelo(nome: str) -> tuple[tuple[int, ...], int, str]:
    versao = tuple(int(parte) for parte in re.findall(r"\d+", nome)[:2])
    categoria = 0 if "flash" in nome else 1
    if "lite" in nome:
        categoria = -1
    return tuple((-parte for parte in versao)), categoria, nome


def _modelos_da_resposta(modelos: Iterable[Any]) -> tuple[str, ...]:
    encontrados: set[str] = set()
    for modelo in modelos:
        acoes = getattr(modelo, "supported_actions", None) or []
        nome = _nome_curto(getattr(modelo, "name", None))
        if nome and "generateContent" in acoes and _eh_modelo_texto(nome):
            encontrados.add(nome)
    return tuple(sorted(encontrados, key=_ordem_modelo))


def descobrir_modelos_ativos(cliente: Any) -> tuple[str, ...]:
    global _cache_modelos, _cache_expira_em

    agora = time.monotonic()
    if _cache_modelos and agora < _cache_expira_em:
        return _cache_modelos

    try:
        _cache_modelos = _modelos_da_resposta(cliente.models.list())
    except Exception as erro:
        LOGGER.warning("Nao foi possivel consultar modelos Gemini ativos: %s", erro)
    if not _cache_modelos:
        _cache_modelos = MODELOS_RESERVA
    _cache_expira_em = agora + CACHE_SEGUNDOS
    return _cache_modelos


def _ordem_economica(nome: str) -> tuple[int, tuple[int, ...], str]:
    if "flash-lite" in nome:
        categoria = 0
    elif "flash" in nome:
        categoria = 1
    else:
        categoria = 2
    versao = tuple(int(parte) for parte in re.findall(r"\d+", nome)[:2])
    return categoria, tuple((-parte for parte in versao)), nome


def sequencia_modelos(
    cliente: Any,
    modelo_principal: str,
    *,
    priorizar_economia: bool = False,
) -> tuple[str, ...]:
    principal = _nome_curto(modelo_principal)
    if not principal:
        raise ValueError("O nome do modelo principal nao pode ser vazio.")
    ativos = descobrir_modelos_ativos(cliente)
    if priorizar_economia:
        ativos = tuple(sorted(ativos, key=_ordem_economica))
    return tuple(dict.fromkeys((principal, *ativos)))


def _codigo_erro(erro: Exception) -> int | None:
    candidatos = (
        getattr(erro, "status_code", None),
        getattr(erro, "code", None),
        getattr(getattr(erro, "response", None), "status_code", None),
    )
    for candidato in candidatos:
        if isinstance(candidato, int):
            return candidato
        if isinstance(candidato, str) and candidato.isdigit():
            return int(candidato)
        texto = str(candidato or "")
        encontrado = re.search(r"\b(\d{3})\b", texto)
        if encontrado:
            return int(encontrado.group(1))
    encontrado = re.search(r"\b(408|429|500|502|503|504)\b", str(erro))
    return int(encontrado.group(1)) if encontrado else None


def erro_transitorio(erro: Exception) -> bool:
    codigo = _codigo_erro(erro)
    if codigo == 404 or codigo == 408 or codigo == 409 or codigo == 429:
        return True
    if codigo is not None and 500 <= codigo <= 599:
        return True
    if codigo is not None:
        return False
    classe = type(erro).__name__.lower()
    if "timeout" in classe or "connection" in classe:
        return True
    mensagem = str(erro).lower()
    return any(
        termo in mensagem
        for termo in (
            "resource_exhausted",
            "temporari",
            "temporary",
            "temporarily unavailable",
            "service unavailable",
            "too many requests",
            "rate limit",
            "timed out",
            "connection error",
            "model not found",
            "not supported for generatecontent",
        )
    )


def gerar_com_fallback(
    cliente: Any,
    modelo_principal: str,
    chamada: Callable[[str], _T],
    *,
    limite_tentativas: int | None = None,
    priorizar_economia: bool = False,
) -> _T:
    modelos = sequencia_modelos(
        cliente,
        modelo_principal,
        priorizar_economia=priorizar_economia,
    )
    if limite_tentativas is not None:
        modelos = modelos[:limite_tentativas]
    for indice, modelo in enumerate(modelos):
        try:
            return chamada(modelo)
        except Exception as erro:
            if not erro_transitorio(erro) or indice == len(modelos) - 1:
                raise
            LOGGER.warning(
                "Modelo Gemini %s falhou de forma transitória; tentando %s: %s",
                modelo,
                modelos[indice + 1],
                erro,
            )
    raise RuntimeError("Nenhum modelo Gemini foi tentado.")
