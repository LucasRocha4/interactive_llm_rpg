import io
import random
from copy import deepcopy
from contextlib import redirect_stdout
from unittest.mock import patch

from llm_interactive_rpg.app.main import executar_turno
from llm_interactive_rpg.app.motor.regras_engine import MotorRegras
from llm_interactive_rpg.app.pipeline.motor_bridge import (
    despachar_para_motor,
    montar_pedido_motor,
)
from llm_interactive_rpg.app.pipeline.schemas import IntentJogador


class DadosFixos(random.Random):
    def __init__(self, *valores):
        super().__init__(0)
        self.valores = iter(valores)

    def randint(self, a, b):
        valor = next(self.valores)
        assert a <= valor <= b
        return valor


def personagem():
    return {
        "id": "jogador",
        "nivel": 1,
        "atributos": {"garra": 3, "manha": 2, "pulo": 3, "acaso": 1},
        "coracoes": {"atual": 6, "maximo": 6},
        "infeccao": {"atual": 0, "maximo": 5},
        "equipamentos": ["estilingue"],
        "inventario": {"pedra": 2, "banana_curativa": 0, "banana_mistica": 0},
        "condicoes": [],
        "turnos_caido": 0,
        "tecnicas_disponiveis": [],
    }


def cena():
    return {
        "inimigos": [
            {
                "id": "rato_01",
                "tipo": "inimigo",
                "nivel": 1,
                "defesa": 10,
                "protecao": 0,
                "coracoes": {"atual": 4, "maximo": 4},
                "atributos": {"pulo": 1, "acaso": 1},
            }
        ],
        "npcs": [],
        "objetos": [],
        "locais": [],
        "turno": 0,
        "fatos": [],
    }


def test_json_llm_valido_passa_pela_bridge_e_atualiza_estado():
    intent = IntentJogador.model_validate(
        {
            "intencao": "atacar",
            "acao_id": "Golpear",
            "equipamento_id": "Estilingue",
            "alvo": {"tipo": "inimigo", "id": "rato_01"},
        }
    )
    jogador = personagem()
    contexto = cena()
    motor = MotorRegras(DadosFixos(15))

    pedido = montar_pedido_motor(intent, "integracao-valida")
    resultado = despachar_para_motor(pedido, jogador, contexto, motor)

    assert pedido.acao_id == "golpear"
    assert pedido.parametros.equipamento_id == "estilingue"
    assert resultado.sucesso is True
    assert resultado.motivo_bloqueio is None
    assert resultado.acao_executada == "golpear"
    assert resultado.rolagens[0]["valor_natural"] == 15
    assert resultado.impacto_mecanico["dano_final"] == 2
    assert jogador["inventario"]["pedra"] == 1
    assert contexto["inimigos"][0]["coracoes"]["atual"] == 2
    assert resultado.estado_atualizado == {"personagem": jogador, "cena": contexto}


def test_acao_sem_recurso_e_bloqueada_sem_mutar_estado():
    intent = IntentJogador.model_validate(
        {
            "intencao": "atacar",
            "equipamento_id": "estilingue",
            "alvo": {"tipo": "inimigo", "id": "rato_01"},
        }
    )
    jogador = personagem()
    jogador["inventario"]["pedra"] = 0
    contexto = cena()
    motor = MotorRegras(random.Random(7))
    estado_antes = deepcopy((jogador, contexto))
    rng_antes = motor.rng.getstate()

    pedido = montar_pedido_motor(intent, "integracao-bloqueada")
    resultado = despachar_para_motor(pedido, jogador, contexto, motor)

    assert resultado.sucesso is False
    assert resultado.motivo_bloqueio is not None
    assert resultado.motivo_bloqueio.codigo == "RECURSO_INSUFICIENTE"
    assert (jogador, contexto) == estado_antes
    assert motor.rng.getstate() == rng_antes
    assert resultado.estado_atualizado == {"personagem": jogador, "cena": contexto}


def test_turno_nao_promove_estado_candidato_quando_acao_falha():
    intent = IntentJogador.model_validate(
        {
            "intencao": "atacar",
            "equipamento_id": "estilingue",
            "alvo": {"tipo": "inimigo", "id": "rato_01"},
        }
    )
    jogador = personagem()
    contexto = cena()
    estado_antes = deepcopy((jogador, contexto))

    with (
        patch("llm_interactive_rpg.app.main.interpretar_acao", return_value=intent),
        patch("llm_interactive_rpg.app.main.salvar_na_outbox"),
        redirect_stdout(io.StringIO()),
    ):
        resultado = executar_turno(
            "atire no rato",
            jogador,
            contexto,
            MotorRegras(DadosFixos(1)),
        )

    assert resultado.sucesso is False
    assert (jogador, contexto) == estado_antes
    assert resultado.estado_atualizado["personagem"]["inventario"]["pedra"] == 1


def test_id_invalido_e_bloqueado_pela_bridge_sem_deslocar_motor():
    intent = IntentJogador(
        intencao="atacar",
        equipamento_id="arma_inexistente",
        alvo={"tipo": "inimigo", "id": "rato_01"},
    )
    pedido = montar_pedido_motor(intent, "integracao-id-invalido")
    jogador = personagem()
    contexto = cena()
    estado_antes = deepcopy((jogador, contexto))

    resultado = despachar_para_motor(pedido, jogador, contexto, MotorRegras())

    assert resultado.sucesso is False
    assert resultado.motivo_bloqueio.codigo == "EQUIPAMENTO_INVALIDO"
    assert (jogador, contexto) == estado_antes


def test_turno_chama_parser_uma_vez_e_imprime_envelope_unico():
    intent = IntentJogador.model_validate(
        {
            "intencao": "atacar",
            "equipamento_id": "estilingue",
            "alvo": {"tipo": "inimigo", "id": "rato_01"},
        }
    )
    jogador = personagem()
    contexto = cena()
    saida = io.StringIO()

    with (
        patch(
            "llm_interactive_rpg.app.main.interpretar_acao",
            return_value=intent,
        ) as parser,
        patch("llm_interactive_rpg.app.main.salvar_na_outbox") as salvar,
        patch(
            "llm_interactive_rpg.app.main.narrar_resultado",
            return_value="A pedra atinge o rato com um estalo certeiro.",
        ) as narrador,
        redirect_stdout(saida),
    ):
        resultado = executar_turno(
            "atire uma pedra no rato",
            jogador,
            contexto,
            MotorRegras(DadosFixos(15)),
        )

    parser.assert_called_once()
    salvar.assert_called_once()
    assert resultado.sucesso is True
    assert saida.getvalue().strip() == "A pedra atinge o rato com um estalo certeiro."
    narrador.assert_called_once_with("atire uma pedra no rato", resultado)
    assert set(
        [
            "sucesso",
            "motivo_bloqueio",
            "acao_executada",
            "rolagens",
            "impacto_mecanico",
            "fatos_para_narracao",
            "estado_atualizado",
        ]
    ).issubset(resultado.model_dump(mode="json"))
