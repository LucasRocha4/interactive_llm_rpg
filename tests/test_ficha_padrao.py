import json
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from llm_interactive_rpg.app.main import FICHA_PADRAO_ID, main, personagem_simulado
from llm_interactive_rpg.app.motor.regras_engine import REGRAS_ROOT, MotorRegras
from llm_interactive_rpg.app.pipeline.parser_ia import criar_cena_atual
from llm_interactive_rpg.app.pipeline.schemas import ParametrosMotor, PedidoMotor, TesteMotor


class TestFichaPadrao(unittest.TestCase):
    def setUp(self):
        self.motor = MotorRegras()
        with (REGRAS_ROOT / "exemplos_de_ficha.json").open(encoding="utf-8") as arquivo:
            self.ficha = next(ficha for ficha in json.load(arquivo) if ficha["id"] == FICHA_PADRAO_ID)

    def test_carrega_ficha_e_inicializa_estado_das_regras(self):
        personagem = personagem_simulado(self.motor)
        escolhas = self.ficha["escolhas"]
        self.assertEqual(personagem["id"], self.ficha["id"])
        self.assertEqual(personagem["nome"], self.ficha["nome"])
        self.assertEqual(personagem["atributos"], self.ficha["atributos_calculados"])
        self.assertEqual(personagem["defesa"], self.ficha["defesa"])
        for campo in ("nivel", "pelagem_id", "oficio_id", "defeito_id"):
            self.assertEqual(personagem[campo], escolhas[campo])
        self.assertEqual(personagem["equipamentos"], [escolhas["equipamento_id"]])
        self.assertEqual(personagem["coracoes"], {"atual": 6, "maximo": 6})
        self.assertEqual(personagem["infeccao"], {"atual": 0, "maximo": 5})
        self.assertEqual(personagem["tecnicas_disponiveis"], ["lutador_n1_bater_no_peito"])
        self.assertFalse(any(npc["id"] == "bongo" for npc in criar_cena_atual(personagem)["npcs"]))

    def test_le_fonte_e_reinicia_estado_a_cada_chamada(self):
        ficha = dict(self.ficha, nome="Ficha modificada")
        ficha["atributos_calculados"] = dict(ficha["atributos_calculados"], garra=2)
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "exemplos_de_ficha.json"
            caminho.write_text(json.dumps([ficha]), encoding="utf-8")
            with patch("llm_interactive_rpg.app.main.REGRAS_ROOT", Path(diretorio)):
                primeiro = personagem_simulado(self.motor)
                self.assertEqual(primeiro["nome"], "Ficha modificada")
                atributos = primeiro["atributos"]
                coracoes = primeiro["coracoes"]
                assert isinstance(atributos, dict) and isinstance(coracoes, dict)
                self.assertEqual(atributos["garra"], 2)
                atributos["garra"] = 99
                coracoes["atual"] = 0
                segundo = personagem_simulado(self.motor)
                atributos_segundo = segundo["atributos"]
                coracoes_segundo = segundo["coracoes"]
                assert isinstance(atributos_segundo, dict) and isinstance(coracoes_segundo, dict)
                self.assertEqual(atributos_segundo["garra"], 2)
                self.assertEqual(coracoes_segundo["atual"], 6)
                self.assertEqual(json.loads(caminho.read_text(encoding="utf-8")), [ficha])

    def test_ficha_ausente_ou_duplicada_nao_e_silenciada(self):
        with tempfile.TemporaryDirectory() as diretorio:
            caminho = Path(diretorio) / "exemplos_de_ficha.json"
            with patch("llm_interactive_rpg.app.main.REGRAS_ROOT", Path(diretorio)):
                for fichas in ([], [self.ficha, self.ficha]):
                    caminho.write_text(json.dumps(fichas), encoding="utf-8")
                    with self.assertRaisesRegex(ValueError, FICHA_PADRAO_ID):
                        personagem_simulado(self.motor)

    def test_terminal_usa_ficha_padrao(self):
        with (
            patch.dict("os.environ", {"GEMINI_API_KEY": "teste"}),
            patch("builtins.input", side_effect=["observar", "sair"]),
            patch("llm_interactive_rpg.app.main.configurar_logs"),
            patch("llm_interactive_rpg.app.main.executar_turno") as executar,
            patch("django.db.models.query.QuerySet.first", return_value=None) as buscar,
        ):
            main()
        self.assertEqual(buscar.call_count, 2)
        personagem = executar.call_args.args[1]
        self.assertEqual(personagem["id"], FICHA_PADRAO_ID)
        self.assertEqual(personagem["nome"], self.ficha["nome"])

    def test_ficha_padrao_funciona_no_motor(self):
        personagem = personagem_simulado(self.motor)
        cena = criar_cena_atual(personagem)
        self.motor.rng = random.Random(0)
        pedido = PedidoMotor(
            requisicao_id="teste",
            tipo="atacar",
            parametros=ParametrosMotor(alvo_id="rato_01", equipamento_id="machado_de_pedra"),
            teste=TesteMotor(),
        )
        resultado = self.motor.executar(pedido, personagem, cena)
        self.assertEqual(resultado.status, "executado")
        self.assertTrue(resultado.sucesso)
        assert resultado.rolagem is not None
        self.assertEqual(resultado.rolagem.modificador, self.ficha["atributos_calculados"]["garra"])
        self.assertEqual(cena["inimigos"][0]["coracoes"]["atual"], 0)


if __name__ == "__main__":
    unittest.main()
