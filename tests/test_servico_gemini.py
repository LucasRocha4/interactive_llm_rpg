import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase

from app.models import Campaign, Character, Item, NPC
from llm_interactive_rpg.app.pipeline.schemas import AlvoJogador, IntentJogador
from llm_interactive_rpg.app.pipeline.servico_gemini import (
    interpretar_acao_da_campanha,
    montar_contexto_do_banco,
)


class TestServicoGemini(TestCase):
    def setUp(self):
        usuario = get_user_model().objects.create_user(username="jogador")
        self.campanha = Campaign.objects.create(
            dono=usuario,
            nome="A Jornada do Rio",
            descricao="Encontrar a nascente.",
            local_atual="rio",
        )
        self.ficha = Character.objects.create(
            campanha=self.campanha,
            nome="Bongo",
            pelagem_id="marrom",
            oficio_id="lutador",
            defeito_id="cheiro_de_pantano",
            equipamentos=["machado_de_pedra"],
        )
        self.npc = NPC.objects.create(
            campanha=self.campanha,
            nome="Lia",
            local="rio",
            descricao="Uma guia da região.",
        )

    def test_contexto_vem_da_campanha_ficha_npcs_e_itens_do_banco(self):
        contexto = montar_contexto_do_banco(self.campanha, self.ficha)

        self.assertEqual(contexto["campanha"]["nome"], "A Jornada do Rio")
        self.assertEqual(contexto["campanha"]["local_atual"], "rio")
        self.assertEqual(contexto["personagem"]["nome"], "Bongo")
        self.assertEqual(contexto["npcs"][0]["nome"], "Lia")
        self.assertIn("machado_de_pedra", contexto["equipamentos_validos"])
        self.assertTrue(Item.objects.exists())

    def test_interpretacao_usa_gemini_mockado_e_retorna_intent_pydantic(self):
        intent = IntentJogador(
            intencao="investigar",
            alvo=AlvoJogador(tipo="local", id="rio"),
        )
        cliente = SimpleNamespace(
            models=SimpleNamespace(
                generate_content=Mock(return_value=SimpleNamespace(parsed=intent))
            )
        )
        with (
            patch.dict(os.environ, {"GEMINI_API_KEY": "chave-de-teste"}),
            patch("llm_interactive_rpg.app.pipeline.parser_ia.genai.Client", return_value=cliente),
        ):
            resultado = interpretar_acao_da_campanha(
                "investigo o rio",
                self.campanha,
                self.ficha,
                self.ficha.para_estado_motor(),
                montar_contexto_do_banco(self.campanha, self.ficha),
            )

        self.assertIsInstance(resultado, IntentJogador)
        self.assertEqual(resultado.alvo.id, "rio")
        chamada = cliente.models.generate_content
        self.assertIn("A Jornada do Rio", chamada.call_args.kwargs["config"].system_instruction)
        self.assertIn("machado_de_pedra", chamada.call_args.kwargs["config"].system_instruction)
