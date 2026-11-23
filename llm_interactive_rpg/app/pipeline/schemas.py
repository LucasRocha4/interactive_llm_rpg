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
TipoDificuldade = Literal["facil", "media", "dificil", "absurda"]


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
    objeto_id: str | None = None
    alvo: AlvoJogador
    quantidade: int | None = Field(default=1, ge=1)
    distancia_m: float | None = Field(default=None, ge=0)
    tamanho_objeto: str | None = None
    atributo_id: TipoAtributo | None = None
    dificuldade: TipoDificuldade | None = None
    categoria_item: str | None = None
    vantagem: bool = False
    desvantagem: bool = False
    perguntas_pendentes: list[str] = Field(default_factory=list)


class ParametrosMotor(ModeloEstrito):
    alvo_id: str | None = None
    equipamento_id: str | None = None
    objeto_id: str | None = None
    quantidade: int | None = Field(default=None, ge=1)
    distancia_m: float | None = None
    tamanho_objeto: str | None = None
    categoria_item: str | None = None


class TesteMotor(ModeloEstrito):
    atributo_id: TipoAtributo | None = None
    dificuldade: TipoDificuldade | None = None
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
    perguntas_pendentes: list[str] = Field(default_factory=list)

    def to_json_payload(self) -> dict[str, object]:
        return self.model_dump(mode="json")


class ResultadoRolagem(ModeloEstrito):
    executada: bool
    dados_rolados: list[int] = Field(default_factory=list)
    dado_escolhido: int | None = None
    modificador: int = 0
    total: int | None = None
    alvo_numero: int | None = None
    critico: bool = False
    mancada: bool = False


class ResultadoMotor(ModeloEstrito):
    status: Literal["executado", "aguardando_esclarecimento", "bloqueado_condicao"]
    sucesso: bool | None = None
    rolagem: ResultadoRolagem | None = None
    dano_bruto: int = 0
    protecao_aplicada: int = 0
    dano_final: int = 0
    efeitos: list[str] = Field(default_factory=list)
    alteracoes_personagem: list[str] = Field(default_factory=list)
