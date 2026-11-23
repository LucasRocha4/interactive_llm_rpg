from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from .schemas import IntentJogador, ParametrosMotor, PedidoMotor, ResultadoMotor, TesteMotor


LOGGER = logging.getLogger("rpg.interpreter")
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
            objeto_id=intent.objeto_id,
            quantidade=intent.quantidade,
            distancia_m=intent.distancia_m,
            tamanho_objeto=intent.tamanho_objeto,
            categoria_item=intent.categoria_item,
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
    return motor.executar(pedido, personagem, contexto_cena)
