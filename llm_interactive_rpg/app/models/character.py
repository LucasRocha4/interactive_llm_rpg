from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .campaign import Campaign
from .catalogos import carregar_catalogo, registros_por_id, validar_id

_ATRIBUTOS_JSON = {item["id"] for item in carregar_catalogo("atributos")}
_REGRAS_GERAIS = {item["id"]: item for item in carregar_catalogo("regras_gerais")}
ATRIBUTOS = tuple(sorted(_ATRIBUTOS_JSON))
ATRIBUTO_MAXIMO = _REGRAS_GERAIS["evolucao"]["valores"]["maximo"]
INFECCAO_MAXIMA = _REGRAS_GERAIS["infeccao"]["valores"]["maximo"]
CORACOES_INICIAIS = _REGRAS_GERAIS["coracoes"]["valores"]["iniciais"]


def coracoes_iniciais():
    return {"atual": CORACOES_INICIAIS, "maximo": CORACOES_INICIAIS}


def infeccao_inicial():
    return {"atual": 0, "maximo": INFECCAO_MAXIMA}


class Character(models.Model):
    """Ficha do macaco. Pelagem, ofício, defeito, equipamentos e técnicas
    são ids do catálogo em app/regras/*.json."""

    campanha = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="personagens",
    )

    nome = models.CharField(max_length=100)
    nivel = models.PositiveSmallIntegerField(
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(max(_REGRAS_GERAIS["evolucao"]["valores"]["niveis"])),
        ],
    )
    pelagem_id = models.CharField(max_length=60)
    oficio_id = models.CharField(max_length=60)
    defeito_id = models.CharField(max_length=60)

    # {"garra": 3, "manha": 1, "pulo": 3, "acaso": 1}
    atributos = models.JSONField(default=dict, blank=True)
    # {"atual": 6, "maximo": 6}
    coracoes = models.JSONField(default=coracoes_iniciais)
    # {"atual": 0, "maximo": 5}; o defeito Mutação da Praga começa em 1
    infeccao = models.JSONField(default=infeccao_inicial)

    # ids de equipamentos em uso: ["machado_de_pedra"]
    equipamentos = models.JSONField(default=list, blank=True)
    # {equipamento_id: quantidade}: {"pedra": 6, "banana_curativa": 3}
    inventario = models.JSONField(default=dict, blank=True)
    condicoes = models.JSONField(default=list, blank=True)
    tecnicas_disponiveis = models.JSONField(default=list, blank=True)

    # estado de jogo: usos de técnicas (cena/dia), turnos de Caído,
    # vantagens ativas, escapes do turno...
    estado = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["campanha"], name="uma_ficha_jogador_por_campanha"
            )
        ]

    @property
    def defesa(self):
        """Regra provisória: 10 + Pulo. Calculada na hora, nunca guardada."""
        return 10 + self.atributos.get("pulo", 0)

    def clean(self):
        super().clean()
        erros = {}

        pelagem = registros_por_id("pelagens").get(self.pelagem_id)
        oficio = registros_por_id("oficios").get(self.oficio_id)
        if pelagem is None:
            erros["pelagem_id"] = "Escolha um ID presente em pelagens.json."
        if oficio is None:
            erros["oficio_id"] = "Escolha um ID presente em oficios.json."
        try:
            validar_id(self.defeito_id, "defeitos", "defeito_id")
        except ValidationError as erro:
            erros.update(erro.message_dict)

        if pelagem is not None and oficio is not None:
            esperados = dict(pelagem["atributos"])
            for bonus in oficio["bonus_atributos"]:
                esperados[bonus["atributo_id"]] += bonus["valor"]
            if not self.atributos:
                self.atributos = esperados
            if not isinstance(self.atributos, dict):
                erros["atributos"] = "Informe os quatro atributos em um objeto JSON."
            else:
                faltando = set(ATRIBUTOS) - set(self.atributos)
                extras = set(self.atributos) - set(ATRIBUTOS)
                if faltando:
                    erros["atributos"] = f"Faltam atributos: {', '.join(sorted(faltando))}."
                if extras:
                    erros["atributos"] = f"Atributos desconhecidos: {', '.join(sorted(extras))}."
            if isinstance(self.atributos, dict) and set(ATRIBUTOS) == set(self.atributos):
                for nome, valor in self.atributos.items():
                    if isinstance(valor, bool) or not isinstance(valor, int) or not 1 <= valor <= ATRIBUTO_MAXIMO:
                        erros["atributos"] = f"{nome} deve ser inteiro entre 1 e {ATRIBUTO_MAXIMO}."
                        break
                else:
                    evolucao = _REGRAS_GERAIS["evolucao"]["valores"]
                    pontos_evolucao = sum(nivel <= self.nivel for nivel in evolucao["niveis"])
                    if self.nivel == 1 and self.atributos != esperados:
                        erros["atributos"] = "No nível 1, os atributos devem corresponder à pelagem e aos bônus do ofício."
                    elif self.nivel > 1 and (
                        any(self.atributos[a] < esperados[a] for a in ATRIBUTOS)
                        or sum(self.atributos.values()) != sum(esperados.values()) + pontos_evolucao
                    ):
                        erros["atributos"] = "Os atributos devem refletir os bônus da ficha e os pontos de evolução previstos nas regras."

        self._validar_medidor("coracoes", self.coracoes, erros)
        self._validar_medidor("infeccao", self.infeccao, erros, maximo_regra=INFECCAO_MAXIMA)

        if self._state.adding and self.defeito_id == "mutacao_da_praga":
            atual = self.infeccao.get("atual", 0) if isinstance(self.infeccao, dict) else 0
            if atual == 0:
                self.infeccao = {"atual": 1, "maximo": INFECCAO_MAXIMA}

        if not isinstance(self.equipamentos, list):
            erros["equipamentos"] = "Informe uma lista de IDs de equipamentos."
        else:
            ids_itens = set(registros_por_id("equipamentos"))
            invalidos = [item_id for item_id in self.equipamentos if not isinstance(item_id, str) or item_id not in ids_itens]
            if invalidos:
                erros["equipamentos"] = f"IDs de equipamento inválidos: {', '.join(sorted(map(str, invalidos)))}."

        if not isinstance(self.inventario, dict):
            erros["inventario"] = "Informe um mapa de ID de item para quantidade."
        else:
            ids_itens = set(registros_por_id("equipamentos"))
            for item_id, quantidade in self.inventario.items():
                if item_id not in ids_itens:
                    erros["inventario"] = f"Item desconhecido no inventário: {item_id}."
                    break
                if isinstance(quantidade, bool) or not isinstance(quantidade, int) or quantidade < 0:
                    erros["inventario"] = f"A quantidade de {item_id} deve ser um inteiro não negativo."
                    break

        ids_tecnicas = registros_por_id("tecnicas")
        if not isinstance(self.tecnicas_disponiveis, list):
            erros["tecnicas_disponiveis"] = "Informe uma lista de IDs de técnicas."
        else:
            invalidas = [
                tecnica_id
                for tecnica_id in self.tecnicas_disponiveis
                if not isinstance(tecnica_id, str)
                or tecnica_id not in ids_tecnicas
                or ids_tecnicas[tecnica_id]["oficio_id"] != self.oficio_id
                or ids_tecnicas[tecnica_id]["nivel"] > self.nivel
            ]
            if invalidas:
                erros["tecnicas_disponiveis"] = f"Técnicas indisponíveis para este ofício/nível: {', '.join(invalidas)}."

        if erros:
            raise ValidationError(erros)

        if not self.tecnicas_disponiveis and oficio is not None:
            self.tecnicas_disponiveis = [
                tecnica["id"]
                for tecnica in carregar_catalogo("tecnicas")
                if tecnica["oficio_id"] == self.oficio_id and tecnica["nivel"] <= self.nivel
            ]

    @staticmethod
    def _validar_medidor(campo: str, valores: dict, erros: dict, maximo_regra: int | None = None):
        if not isinstance(valores, dict):
            erros[campo] = "Informe um objeto com 'atual' e 'maximo'."
            return
        atual = valores.get("atual")
        maximo = valores.get("maximo")
        if any(isinstance(v, bool) or not isinstance(v, int) for v in (atual, maximo)):
            erros[campo] = "Os valores 'atual' e 'maximo' devem ser inteiros."
        elif maximo < 1 or atual < 0 or atual > maximo:
            erros[campo] = "O valor atual deve estar entre zero e o máximo."
        elif maximo_regra is not None and maximo != maximo_regra:
            erros[campo] = f"O máximo definido nas regras é {maximo_regra}."

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def para_estado_motor(self) -> dict:
        estado = dict(self.estado or {})
        estado.update(
            {
                "id": str(self.pk) if self.pk else "personagem_novo",
                "nome": self.nome,
                "nivel": self.nivel,
                "pelagem_id": self.pelagem_id,
                "oficio_id": self.oficio_id,
                "defeito_id": self.defeito_id,
                "atributos": dict(self.atributos),
                "coracoes": dict(self.coracoes),
                "infeccao": dict(self.infeccao),
                "defesa": self.defesa,
                "equipamentos": list(self.equipamentos),
                "inventario": dict(self.inventario),
                "condicoes": list(self.condicoes),
                "tecnicas_disponiveis": list(self.tecnicas_disponiveis),
            }
        )
        return estado

    def atualizar_do_estado_motor(self, estado: dict):
        for campo in ("atributos", "coracoes", "infeccao", "equipamentos", "inventario", "condicoes", "tecnicas_disponiveis"):
            if campo in estado:
                setattr(self, campo, estado[campo])
        campos_dinamicos = {
            "turnos_caido", "usos_tecnicas", "ataques_no_turno", "recargas",
            "vantagem_alvo", "protecao_temporaria", "perder_proximo_turno",
            "montado_em", "duracoes", "protecao_temporaria",
        }
        self.estado = {campo: estado[campo] for campo in campos_dinamicos if campo in estado}

    def __str__(self):
        return self.nome
