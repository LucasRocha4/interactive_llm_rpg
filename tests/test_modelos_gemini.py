from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch

from pydantic import ValidationError

from llm_interactive_rpg.app.pipeline import modelos_gemini
from llm_interactive_rpg.app.pipeline.modelos_gemini import (
    descobrir_modelos_ativos,
    erro_transitorio,
    gerar_com_fallback,
    sequencia_modelos,
)
from llm_interactive_rpg.app.pipeline.parser_ia import interpretar_acao


class ErroComStatus(RuntimeError):
    def __init__(self, mensagem, status_code):
        super().__init__(mensagem)
        self.status_code = status_code


class TestModelosGemini(TestCase):
    def setUp(self):
        modelos_gemini._cache_modelos = ()
        modelos_gemini._cache_expira_em = 0.0

    def test_descoberta_filtra_e_ordena_apenas_modelos_de_texto(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-2.5-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.5-flash-lite", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3-pro-image", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemma-4-31b-it", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-omni-flash-preview", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-sem-geracao", supported_actions=["embedContent"]),
        ]

        self.assertEqual(
            descobrir_modelos_ativos(cliente),
            ("gemini-3.8-flash", "gemini-3.5-flash-lite", "gemini-2.5-flash"),
        )

    def test_descoberta_usa_cache_do_processo(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.5-flash", supported_actions=["generateContent"])
        ]

        descobrir_modelos_ativos(cliente)
        descobrir_modelos_ativos(cliente)

        cliente.models.list.assert_called_once_with()

    def test_sequencia_comeca_pelo_modelo_principal_sem_duplicar(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.5-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
        ]

        self.assertEqual(
            sequencia_modelos(cliente, "models/gemini-3.5-flash"),
            ("gemini-3.5-flash", "gemini-3.8-flash"),
        )

    def test_sequencia_economica_prioriza_lite_flash_e_depois_pro(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-2.5-pro", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-2.5-flash-lite", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.5-flash-lite", supported_actions=["generateContent"]),
        ]

        self.assertEqual(
            sequencia_modelos(
                cliente,
                "gemini-3.5-flash",
                priorizar_economia=True,
            ),
            (
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-2.5-flash-lite",
                "gemini-3.8-flash",
                "gemini-2.5-pro",
            ),
        )

    def test_fallback_troca_modelo_em_erro_transitorio(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.5-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
        ]
        chamada = Mock(side_effect=[ErroComStatus("limite", 429), "ok"])

        self.assertEqual(gerar_com_fallback(cliente, "gemini-3.5-flash", chamada), "ok")
        self.assertEqual([item.args[0] for item in chamada.call_args_list], ["gemini-3.5-flash", "gemini-3.8-flash"])

    def test_erro_definitivo_nao_troca_modelo(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.5-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
        ]
        chamada = Mock(side_effect=ErroComStatus("autenticacao", 401))

        with self.assertRaisesRegex(RuntimeError, "autenticacao"):
            gerar_com_fallback(cliente, "gemini-3.5-flash", chamada)

        chamada.assert_called_once_with("gemini-3.5-flash")
        self.assertFalse(erro_transitorio(ErroComStatus("autenticacao", 401)))

    def test_parser_nao_esconde_erro_de_validacao_com_outro_modelo(self):
        cliente = Mock()
        cliente.models.list.return_value = [
            SimpleNamespace(name="models/gemini-3.5-flash", supported_actions=["generateContent"]),
            SimpleNamespace(name="models/gemini-3.8-flash", supported_actions=["generateContent"]),
        ]
        cliente.models.generate_content.return_value = SimpleNamespace(parsed=object(), text="{")

        with patch.dict("os.environ", {"GEMINI_API_KEY": "teste"}):
            with self.assertRaises(ValidationError):
                interpretar_acao("investigar", {"id": "heroi"}, {}, cliente=cliente)

        cliente.models.generate_content.assert_called_once()
