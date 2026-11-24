import json
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from llm_interactive_rpg.app.pipeline.narrador_ia import (
    narrar_resultado,
    narrativa_fallback,
)
from llm_interactive_rpg.app.pipeline.schemas import MotivoBloqueio, ResultadoMotor


def cliente_com_respostas(*respostas):
    cliente = Mock()
    cliente.models.generate_content.side_effect = respostas
    return cliente


def resultado_executado():
    return ResultadoMotor(
        status="executado",
        sucesso=True,
        acao_executada="golpear",
        dano_final=2,
        fatos_para_narracao=["Rolagem total 15: sucesso.", "Dano final aplicado: 2."],
        impacto_mecanico={"dano_final": 2},
        estado_atualizado={"personagem": {"nome": "Bongo"}, "cena": {}},
    )


def _test_narrador_recebe_apenas_fatos_mecanicos_autorizados():
    cliente = cliente_com_respostas(SimpleNamespace(text="A pedra voa e acerta em cheio!"))

    with patch.dict("os.environ", {"GEMINI_API_KEY": "teste", "GEMINI_NARRATOR_MODEL": "modelo-teste"}):
        narrativa = narrar_resultado("ataco o rato", resultado_executado(), cliente=cliente)

    assert narrativa == "A pedra voa e acerta em cheio!"
    chamada = cliente.models.generate_content.call_args
    assert chamada.kwargs["model"] == "modelo-teste"
    entrada = json.loads(chamada.kwargs["contents"])
    assert entrada["acao_do_jogador"] == "ataco o rato"
    assert entrada["resultado_do_motor"]["dano_final"] == 2
    assert "estado_atualizado" not in entrada["resultado_do_motor"]
    assert "nao role dados" in chamada.kwargs["config"].system_instruction


def _test_narrador_repete_uma_vez_antes_do_fallback():
    cliente = cliente_com_respostas(RuntimeError("temporario"), SimpleNamespace(text="O golpe conecta!"))

    with patch.dict("os.environ", {"GEMINI_API_KEY": "teste"}):
        narrativa = narrar_resultado("golpeio", resultado_executado(), cliente=cliente)

    assert narrativa == "O golpe conecta!"
    assert cliente.models.generate_content.call_count == 2


def _test_narrador_usa_fallback_apos_duas_respostas_vazias():
    cliente = cliente_com_respostas(SimpleNamespace(text=""), SimpleNamespace(text=" "))

    with patch.dict("os.environ", {"GEMINI_API_KEY": "teste"}):
        narrativa = narrar_resultado("golpeio", resultado_executado(), cliente=cliente)

    assert narrativa == "Rolagem total 15: sucesso. Dano final aplicado: 2."
    assert cliente.models.generate_content.call_count == 2


def _test_fallback_de_esclarecimento_nao_finge_execucao():
    resultado = ResultadoMotor(
        status="aguardando_esclarecimento",
        sucesso=False,
        efeitos=["Qual inimigo voce deseja atingir?"],
        motivo_bloqueio=MotivoBloqueio(
            codigo="ESCLARECIMENTO_NECESSARIO",
            detalhe="Qual inimigo voce deseja atingir?",
        ),
    )

    assert narrativa_fallback(resultado) == (
        "Preciso esclarecer uma coisa antes da ação: Qual inimigo voce deseja atingir?"
    )


def _test_fallback_de_bloqueio_exibe_apenas_a_restricao():
    resultado = ResultadoMotor(
        status="bloqueado_condicao",
        sucesso=False,
        motivo_bloqueio=MotivoBloqueio(
            codigo="RECURSO_INSUFICIENTE",
            detalhe="Voce nao possui pedras.",
        ),
    )

    assert narrativa_fallback(resultado) == "A ação não aconteceu: Voce nao possui pedras."


class TestNarradorIA(TestCase):
    def test_narrador_recebe_apenas_fatos_mecanicos_autorizados(self):
        _test_narrador_recebe_apenas_fatos_mecanicos_autorizados()

    def test_narrador_repete_uma_vez_antes_do_fallback(self):
        _test_narrador_repete_uma_vez_antes_do_fallback()

    def test_narrador_usa_fallback_apos_duas_respostas_vazias(self):
        _test_narrador_usa_fallback_apos_duas_respostas_vazias()

    def test_fallback_de_esclarecimento_nao_finge_execucao(self):
        _test_fallback_de_esclarecimento_nao_finge_execucao()

    def test_fallback_de_bloqueio_exibe_apenas_a_restricao(self):
        _test_fallback_de_bloqueio_exibe_apenas_a_restricao()
