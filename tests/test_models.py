from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from app.models import Campaign, Character, Item, NPC


class TestModels(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="jogador", password="teste-seguro"
        )
        self.campanha = Campaign.objects.create(dono=self.usuario, nome="A Clareira")

    def test_ficha_calcula_atributos_e_tecnica_de_nivel_1(self):
        ficha = Character.objects.create(
            campanha=self.campanha,
            nome="Bongo Chulé",
            pelagem_id="marrom",
            oficio_id="lutador",
            defeito_id="cheiro_de_pantano",
        )

        self.assertEqual(ficha.atributos, {"garra": 3, "manha": 1, "pulo": 3, "acaso": 1})
        self.assertEqual(ficha.defesa, 13)
        self.assertEqual(ficha.coracoes, {"atual": 6, "maximo": 6})
        self.assertEqual(ficha.infeccao, {"atual": 0, "maximo": 5})
        self.assertEqual(ficha.tecnicas_disponiveis, ["lutador_n1_bater_no_peito"])

    def test_ids_invalidos_sao_rejeitados(self):
        with self.assertRaises(ValidationError):
            Character.objects.create(
                campanha=self.campanha,
                nome="Ficha inválida",
                pelagem_id="pelagem_inventada",
                oficio_id="lutador",
                defeito_id="cheiro_de_pantano",
            )

        with self.assertRaises(ValidationError):
            Character.objects.create(
                campanha=self.campanha,
                nome="Outra ficha inválida",
                pelagem_id="marrom",
                oficio_id="lutador",
                defeito_id="cheiro_de_pantano",
                equipamentos=["arma_inventada"],
            )

    def test_atributos_e_medidores_invalidos_sao_rejeitados(self):
        with self.assertRaises(ValidationError):
            Character.objects.create(
                campanha=self.campanha,
                nome="Atributos inválidos",
                pelagem_id="marrom",
                oficio_id="lutador",
                defeito_id="cheiro_de_pantano",
                atributos={"garra": 99},
            )

        with self.assertRaises(ValidationError):
            Character.objects.create(
                campanha=self.campanha,
                nome="Infecção inválida",
                pelagem_id="marrom",
                oficio_id="lutador",
                defeito_id="cheiro_de_pantano",
                infeccao={"atual": 6, "maximo": 5},
            )

    def test_migracao_carrega_itens_do_catalogo_de_regras(self):
        machado = Item.objects.get(pk="machado_de_pedra")
        sucata = Item.objects.get(pk="sucata")
        self.assertEqual(machado.dano, 4)
        self.assertEqual(sucata.categoria, Item.Categoria.MATERIAL)

    def test_npc_nao_exige_regras_de_combate_que_nao_estao_definidas(self):
        npc = NPC.objects.create(
            campanha=self.campanha,
            nome="Guia da Clareira",
            descricao="Conhece as trilhas.",
        )
        self.assertIsNone(npc.defesa)
        self.assertIsNone(npc.coracoes)
