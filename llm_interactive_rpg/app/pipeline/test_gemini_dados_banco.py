import os
import unittest

from django.contrib.auth import get_user_model
from django.test import TestCase
from google import genai

from app.models import Campaign, Character, NPC


@unittest.skipUnless(
    os.getenv("GEMINI_API_KEY"),
    "Ignorado: defina GEMINI_API_KEY para executar o teste real do Gemini.",
)
class TestGeminiComDadosDoBanco(TestCase):
    def test_gemini_interpreta_campanha_personagem_e_npc_salvos(self):
        usuario = get_user_model().objects.create_user(username="jogador_teste")
        campanha = Campaign.objects.create(
            dono=usuario,
            nome="A Clareira das Bananas",
            descricao="Uma aventura de teste na floresta.",
            local_atual="Clareira",
        )
        personagem = Character.objects.create(
            campanha=campanha,
            nome="Bongo",
            nivel=1,
            pelagem_id="marrom",
            oficio_id="lutador",
            defeito_id="cheiro_de_pantano",
            equipamentos=["machado_de_pedra"],
        )
        npc = NPC.objects.create(
            campanha=campanha,
            nome="Mila",
            descricao="Uma macaca curandeira que conhece a floresta.",
            local="Clareira",
        )

        texto_para_interpretar = (
            "Resuma em português os dados desta campanha de RPG. "
            "Diga o nome da campanha e do personagem, seus atributos, equipamento "
            "e quem é o NPC. Não invente dados ausentes.\n\n"
            f"Campanha: {campanha.nome}. Descrição: {campanha.descricao}. "
            f"Local: {campanha.local_atual}.\n"
            f"Personagem: {personagem.nome}, nível {personagem.nivel}, "
            f"pelagem {personagem.pelagem_id}, ofício {personagem.oficio_id}, "
            f"defeito {personagem.defeito_id}, atributos {personagem.atributos}, "
            f"corações {personagem.coracoes}, infecção {personagem.infeccao}, "
            f"equipamentos {personagem.equipamentos}.\n"
            f"NPC: {npc.nome}. Descrição: {npc.descricao}. Local: {npc.local}."
        )

        cliente = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resposta = cliente.models.generate_content(
            model=os.getenv("GEMINI_NARRATOR_MODEL", "gemini-3.5-flash-lite"),
            contents=texto_para_interpretar,
        )
        interpretacao = (resposta.text or "").strip()

        print(f"\nInterpretação devolvida pelo Gemini:\n{interpretacao}")
        self.assertTrue(interpretacao, "O Gemini não devolveu uma interpretação em texto.")
