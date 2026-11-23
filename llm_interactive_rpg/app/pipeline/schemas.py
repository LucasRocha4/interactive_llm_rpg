from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


TipoIntencao = Literal[
    "atacar",
    "usar_tecnica",
    "usar_item",
    "mover",
    "investigar",
    "falar",
    "outro",
]
TipoAlvo = Literal["inimigo", "npc", "objeto", "local", "proprio", "nenhum"]
TipoAtributo = Literal["garra", "manha", "pulo", "acaso"]


class ModeloEstrito(BaseModel):
    pass


class AlvoJogador(ModeloEstrito):
    tipo: TipoAlvo
    id: str | None = None
    nome_mencionado: str | None = None


class IntentJogador(ModeloEstrito):
    """Contrato exclusivo da interpretação feita pelo Gemini."""

    intencao: TipoIntencao
    acao_id: str | None = None
    tecnica_id: str | None = None
    equipamento_id: str | None = None
    alvo: AlvoJogador
    quantidade: int | None = Field(default=1, ge=1)
    distancia_m: float | None = Field(default=None, ge=0)
    tamanho_objeto: str | None = None
    atributo_id: TipoAtributo | None = None
    vantagem: bool = False
    desvantagem: bool = False
    perguntas_pendentes: list[str] = Field(default_factory=list)


class ParametrosMotor(ModeloEstrito):
    alvo_id: str | None = None
    equipamento_id: str | None = None
    quantidade: int | None = None
    distancia_m: float | None = None
    tamanho_objeto: str | None = None


class TesteMotor(ModeloEstrito):
    atributo_id: TipoAtributo | None = None
    vantagem: bool = False
    desvantagem: bool = False


class PedidoMotor(ModeloEstrito):
    """Contrato enxuto entregue ao Motor de Regras."""

    requisicao_id: str
    tipo: TipoIntencao
    acao_id: str | None = None
    tecnica_id: str | None = None
    parametros: ParametrosMotor
    teste: TesteMotor

    def to_json_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")
