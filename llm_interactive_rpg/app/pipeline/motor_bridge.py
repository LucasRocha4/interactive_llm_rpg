from __future__ import annotations

import json
import logging
import unicodedata
from copy import deepcopy
from pathlib import Path
from typing import Any

from .schemas import (
    IntentJogador,
    MotivoBloqueio,
    ParametrosMotor,
    PedidoMotor,
    ResultadoMotor,
    TesteMotor,
)


LOGGER = logging.getLogger("rpg.interpreter")
OUTBOX_PATH = Path(__file__).resolve().parents[2] / "ultimo_pedido_motor.json"
REGRAS_ROOT = Path(__file__).resolve().parents[1] / "regras"
ACOES_ESPECIAIS = {
    "levantar",
    "recolher_pedras",
    "dormir",
    "encerrar_cena",
    "equipar",
}


def _chave_normalizada(valor: str) -> str:
    sem_acentos = "".join(
        caractere
        for caractere in unicodedata.normalize("NFKD", valor.strip())
        if not unicodedata.combining(caractere)
    )
    return "_".join(sem_acentos.casefold().replace("-", " ").split())


def _carregar_registros(nome: str) -> list[dict[str, Any]]:
    with (REGRAS_ROOT / f"{nome}.json").open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def _resolver_id(valor: str | None, catalogo: str) -> str | None:
    if valor is None:
        return None
    registros = _carregar_registros(catalogo)
    chave = _chave_normalizada(valor)
    for registro in registros:
        candidatos = {registro["id"], registro.get("nome", "")}
        if chave in {_chave_normalizada(str(candidato)) for candidato in candidatos}:
            return str(registro["id"])
    return valor.strip()


def _resultado_bloqueado(
    pedido: PedidoMotor,
    personagem: dict[str, Any],
    contexto_cena: dict[str, Any] | None,
    codigo: str,
    detalhe: str,
) -> ResultadoMotor:
    return ResultadoMotor(
        status="bloqueado_condicao",
        sucesso=False,
        motivo_bloqueio=MotivoBloqueio(codigo=codigo, detalhe=detalhe),
        acao_executada=pedido.acao_id or pedido.tecnica_id or pedido.tipo,
        impacto_mecanico={
            "recursos_consumidos": {},
            "dano_bruto": 0,
            "protecao_aplicada": 0,
            "dano_final": 0,
            "cura_aplicada": 0,
            "alteracoes_personagem": [],
            "efeitos_aplicados": [],
            "efeitos_expirados": [],
            "estado_alterado": {},
        },
        fatos_para_narracao=[detalhe],
        estado_atualizado={
            "personagem": deepcopy(personagem),
            "cena": deepcopy(contexto_cena or {}),
        },
        efeitos=[detalhe],
    )


def montar_pedido_motor(intent: IntentJogador, requisicao_id: str) -> PedidoMotor:
    pedido = PedidoMotor(
        requisicao_id=requisicao_id,
        tipo=intent.intencao,
        acao_id=_resolver_id(intent.acao_id, "acoes") if intent.acao_id and intent.acao_id not in ACOES_ESPECIAIS else intent.acao_id,
        tecnica_id=_resolver_id(intent.tecnica_id, "tecnicas"),
        parametros=ParametrosMotor(
            alvo_id=intent.alvo.id,
            equipamento_id=_resolver_id(intent.equipamento_id, "equipamentos"),
            objeto_id=intent.objeto_id,
            quantidade=intent.quantidade,
            distancia_m=intent.distancia_m,
            tamanho_objeto=_chave_normalizada(intent.tamanho_objeto) if intent.tamanho_objeto else None,
            categoria_item=_chave_normalizada(intent.categoria_item) if intent.categoria_item else None,
        ),
        teste=TesteMotor(
            atributo_id=intent.atributo_id,
            dificuldade=intent.dificuldade,
            vantagem=intent.vantagem,
            desvantagem=intent.desvantagem,
        ),
        perguntas_pendentes=intent.perguntas_pendentes,
    )
    LOGGER.info(
        "[STEP 4 - ADAPTER] Payload PedidoMotor montado e pronto para despacho: %s",
        json.dumps(pedido.to_json_payload(), ensure_ascii=False),
    )
    return pedido


def salvar_na_outbox(pedido: PedidoMotor) -> None:
    OUTBOX_PATH.write_text(
        json.dumps(pedido.to_json_payload(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def despachar_para_motor(
    pedido: PedidoMotor,
    personagem: dict[str, Any],
    contexto_cena: dict[str, Any] | None = None,
    motor: Any = None,
) -> ResultadoMotor:
    from ..motor.regras_engine import MotorRegras

    motor = motor if motor is not None else MotorRegras()
    acoes_validas = {registro["id"] for registro in _carregar_registros("acoes")} | ACOES_ESPECIAIS
    if pedido.acao_id is not None and pedido.acao_id not in acoes_validas:
        return _resultado_bloqueado(
            pedido,
            personagem,
            contexto_cena,
            "ACAO_INVALIDA",
            f"Acao desconhecida: {pedido.acao_id}.",
        )
    if pedido.tecnica_id is not None and pedido.tecnica_id not in motor.tecnicas:
        return _resultado_bloqueado(
            pedido,
            personagem,
            contexto_cena,
            "TECNICA_INVALIDA",
            f"Tecnica desconhecida: {pedido.tecnica_id}.",
        )
    if pedido.parametros.equipamento_id is not None and pedido.parametros.equipamento_id not in motor.equipamentos:
        return _resultado_bloqueado(
            pedido,
            personagem,
            contexto_cena,
            "EQUIPAMENTO_INVALIDO",
            f"Equipamento desconhecido: {pedido.parametros.equipamento_id}.",
        )
    alvo_id = pedido.parametros.alvo_id
    ids_cena = {
        item.get("id")
        for grupo in ("inimigos", "npcs", "objetos", "locais")
        for item in (contexto_cena or {}).get(grupo, [])
        if item.get("id") is not None
    }
    if alvo_id not in (None, "proprio", personagem.get("id")) and alvo_id not in ids_cena:
        return _resultado_bloqueado(
            pedido,
            personagem,
            contexto_cena,
            "ALVO_INVALIDO",
            f"Alvo nao encontrado na cena: {alvo_id}.",
        )
    categoria = pedido.parametros.categoria_item
    if categoria is not None and categoria not in motor.tabela_itens:
        return _resultado_bloqueado(
            pedido,
            personagem,
            contexto_cena,
            "CATEGORIA_INVALIDA",
            f"Categoria de item desconhecida: {categoria}.",
        )
    return motor.executar(pedido, personagem, contexto_cena)
