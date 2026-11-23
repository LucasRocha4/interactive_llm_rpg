from __future__ import annotations

import importlib
import json
import logging
from pathlib import Path
from typing import Any

from .schemas import IntentJogador, ParametrosMotor, PedidoMotor, TesteMotor


LOGGER = logging.getLogger("rpg.interpreter")
MOTOR_DISPONIVEL = False
OUTBOX_PATH = Path(__file__).resolve().parents[2] / "ultimo_pedido_motor.json"


def montar_pedido_motor(intent: IntentJogador, requisicao_id: str) -> PedidoMotor:
    pedido = PedidoMotor(
        requisicao_id=requisicao_id,
        tipo=intent.intencao,
        acao_id=intent.acao_id,
        tecnica_id=intent.tecnica_id,
        parametros=ParametrosMotor(
            alvo_id=intent.alvo.id,
            equipamento_id=intent.equipamento_id,
            quantidade=intent.quantidade,
            distancia_m=intent.distancia_m,
            tamanho_objeto=intent.tamanho_objeto,
        ),
        teste=TesteMotor(
            atributo_id=intent.atributo_id,
            vantagem=intent.vantagem,
            desvantagem=intent.desvantagem,
        ),
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


def despachar_para_motor(pedido: PedidoMotor, personagem: dict[str, Any]) -> dict[str, Any]:
    LOGGER.info(
        "[STEP 5 - MOTOR DISPATCH] Tentativa de envio ao motor de regras: requisicao_id=%s",
        pedido.requisicao_id,
    )
    if not MOTOR_DISPONIVEL:
        LOGGER.warning(
            "[WARNING] Motor de regras nao conectado. Disponibilizando payload em fila/arquivo JSON (outbox): %s",
            OUTBOX_PATH,
        )
        salvar_na_outbox(pedido)
        return {"status": "fora_da_fila", "pedido": pedido.to_json_payload()}

    candidatos = ("motor_regras", "app.motor_regras", "llm_interactive_rpg.app.motor_regras")
    for nome_modulo in candidatos:
        try:
            modulo = importlib.import_module(nome_modulo)
            break
        except ImportError:
            continue
    else:
        LOGGER.warning(
            "[WARNING] Motor de regras nao encontrado. Disponibilizando payload em fila/arquivo JSON (outbox): %s",
            OUTBOX_PATH,
        )
        salvar_na_outbox(pedido)
        return {"status": "fora_da_fila", "pedido": pedido.to_json_payload()}

    for nome_funcao in ("executar_pedido", "despachar", "processar_pedido"):
        funcao = getattr(modulo, nome_funcao, None)
        if callable(funcao):
            resultado = funcao(pedido, personagem)
            LOGGER.info("[STEP 5 - MOTOR DISPATCH] Motor respondeu: %s", resultado)
            return resultado

    LOGGER.error("[STEP 5 - MOTOR DISPATCH] Motor importado, mas nao possui funcao de despacho conhecida.")
    salvar_na_outbox(pedido)
    return {"status": "fora_da_fila", "pedido": pedido.to_json_payload()}
