import random
import io
import unittest
from copy import deepcopy
from contextlib import redirect_stdout
from unittest.mock import patch

from llm_interactive_rpg.app.main import executar_turno
from llm_interactive_rpg.app.motor.regras_engine import MotorRegras
from llm_interactive_rpg.app.pipeline.motor_bridge import montar_pedido_motor
from llm_interactive_rpg.app.pipeline.parser_ia import interpretar_acao
from llm_interactive_rpg.app.pipeline.schemas import (
    AlvoJogador, IntentJogador, ParametrosMotor, PedidoMotor, TesteMotor,
)


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
        "id": "jogador", "nivel": 1,
        "atributos": {"garra": 3, "manha": 2, "pulo": 3, "acaso": 1},
        "coracoes": {"atual": 6, "maximo": 6},
        "infeccao": {"atual": 0, "maximo": 5},
        "equipamentos": ["machado_de_pedra", "estilingue", "lanca_de_graveto"],
        "inventario": {"pedra": 3, "banana_curativa": 2, "banana_mistica": 8, "sucata": 2},
        "condicoes": [], "turnos_caido": 0, "tecnicas_disponiveis": [],
    }


def cena():
    return {"inimigos": [{
        "id": "rato", "tipo": "inimigo", "nivel": 1, "tamanho": "grande",
        "atributos": {"acaso": 1, "pulo": 1, "manha": 1},
        "defesa": 12, "protecao": 1, "coracoes": {"atual": 20, "maximo": 20},
    }], "npcs": [], "turno": 0}


def pedido(tipo="outro", acao=None, *, tecnica=None, alvo=None, equipamento=None, atributo=None, dificuldade=None, quantidade=1, distancia=None, categoria=None, perguntas=None):
    return PedidoMotor(
        requisicao_id="teste", tipo=tipo, acao_id=acao, tecnica_id=tecnica,
        parametros=ParametrosMotor(alvo_id=alvo, equipamento_id=equipamento, quantidade=quantidade, distancia_m=distancia, categoria_item=categoria),
        teste=TesteMotor(atributo_id=atributo, dificuldade=dificuldade),
        perguntas_pendentes=perguntas or [],
    )


class TestMotorRegras(unittest.TestCase):
    def setUp(self):
        self.motor = MotorRegras(random.Random(42))
        self.personagem = personagem()
        self.cena = cena()

    def test_dificuldades(self):
        self.assertEqual([self.motor.obter_valor_dificuldade(x) for x in ("facil", "media", "dificil", "absurda")], [8, 12, 16, 20])
        with self.assertRaises(KeyError):
            self.motor.obter_valor_dificuldade("inexistente")

    def test_vantagem_desvantagem_e_cancelamento(self):
        for vantagem, desvantagem, esperado, quantidade in [(True, False, max, 2), (False, True, min, 2), (True, True, None, 1), (False, False, None, 1)]:
            with self.subTest(vantagem=vantagem, desvantagem=desvantagem):
                rng = random.Random(7)
                rolagem = self.motor.rolar_teste(2, 12, vantagem, desvantagem, rng)
                gerador = random.Random(7)
                dados = [gerador.randint(1, 20) for _ in range(quantidade)]
                self.assertEqual(rolagem.dados_rolados, dados)
                self.assertEqual(rolagem.dado_escolhido, esperado(dados) if esperado else dados[0])

    def test_critico_e_mancada(self):
        critico = self.motor.rolar_teste(-100, 50, rng=DadosFixos(20))
        manc = self.motor.rolar_teste(100, 8, rng=DadosFixos(1))
        self.assertTrue(self.motor._sucesso(critico))
        self.assertFalse(self.motor._sucesso(manc))
        self.assertEqual(self.motor.calcular_dano(4, 1, True), (8, 1, 7))
        self.assertEqual(self.motor.calcular_dano(2, 10), (2, 2, 0))
        with self.assertRaises(ValueError):
            self.motor.calcular_dano(-1, 0)

    def test_ataque_critico_e_municao(self):
        self.motor.rng = DadosFixos(20)
        resultado = self.motor.executar(pedido("atacar", alvo="rato", equipamento="estilingue"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual((resultado.dano_bruto, resultado.protecao_aplicada, resultado.dano_final), (4, 1, 3))
        self.assertEqual(self.cena["inimigos"][0]["coracoes"]["atual"], 17)
        self.assertEqual(self.personagem["inventario"]["pedra"], 2)

    def test_erro_ataque_gasta_pedra_e_mancada_nao_causa_dano(self):
        self.motor.rng = DadosFixos(1)
        resultado = self.motor.executar(pedido("atacar", alvo="rato", equipamento="estilingue"), self.personagem, self.cena)
        self.assertFalse(resultado.sucesso)
        self.assertTrue(resultado.rolagem.mancada)
        self.assertEqual(resultado.dano_final, 0)
        self.assertEqual(self.personagem["inventario"]["pedra"], 2)

    def test_sem_pedra_ou_alvo_nao_muta(self):
        self.personagem["inventario"]["pedra"] = 0
        antes = deepcopy((self.personagem, self.cena))
        resultado = self.motor.executar(pedido("atacar", alvo="rato", equipamento="estilingue"), self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")
        self.assertEqual((self.personagem, self.cena), antes)
        resultado = self.motor.executar(pedido("atacar", alvo="inexistente", equipamento="machado_de_pedra"), self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")
        self.assertEqual((self.personagem, self.cena), antes)

    def test_caido_recuperacao_e_bloqueio(self):
        self.motor.aplicar_dano(self.personagem, 50)
        self.assertEqual(self.personagem["coracoes"]["atual"], 0)
        self.assertIn("caido", self.personagem["condicoes"])
        antes = deepcopy(self.personagem)
        resultado = self.motor.executar(pedido("atacar", alvo="rato", equipamento="machado_de_pedra"), self.personagem, self.cena)
        self.assertEqual(resultado.status, "bloqueado_condicao")
        self.assertEqual(self.personagem, antes)
        self.motor.rng = DadosFixos(11)
        resultado = self.motor.executar(pedido(acao="levantar"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self.personagem["coracoes"]["atual"], 1)
        self.assertNotIn("caido", self.personagem["condicoes"])

    def test_tres_falhas_morte_permanente(self):
        self.motor.aplicar_dano(self.personagem, 6)
        self.motor.rng = DadosFixos(1, 1, 1)
        for _ in range(3):
            self.assertFalse(self.motor.executar(pedido(acao="levantar"), self.personagem, self.cena).sucesso)
        self.assertIn("morto", self.personagem["condicoes"])
        resultado = self.motor.executar(pedido("usar_item", equipamento="banana_curativa"), self.personagem, self.cena)
        self.assertEqual(resultado.status, "bloqueado_condicao")

    def test_cura_item_e_infeccao(self):
        self.motor.aplicar_dano(self.personagem, 6)
        resultado = self.motor.executar(pedido("usar_item", equipamento="banana_curativa"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self.personagem["inventario"]["banana_curativa"], 1)
        self.motor.aplicar_infeccao(self.personagem, 10)
        self.assertEqual(self.personagem["infeccao"]["atual"], 5)
        self.assertTrue({"morto", "zumbi"}.issubset(self.personagem["condicoes"]))

    def test_perguntas_impedem_rolagem_e_mutacao(self):
        intent = IntentJogador(intencao="atacar", alvo=AlvoJogador(tipo="inimigo", id="rato"), dificuldade="media", perguntas_pendentes=["Qual arma?"])
        motor_pedido = montar_pedido_motor(intent, "id")
        self.assertEqual(motor_pedido.teste.dificuldade, "media")
        antes = deepcopy((self.personagem, self.cena))
        resultado = self.motor.executar(motor_pedido, self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")
        self.assertEqual((self.personagem, self.cena), antes)

    def test_coletar_pedras(self):
        self.motor.rng = DadosFixos(10)
        resultado = self.motor.executar(pedido(acao="recolher_pedras"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(resultado.rolagem.alvo_numero, 8)
        self.assertEqual(self.personagem["inventario"]["pedra"], 4)

    def test_dificuldade_contextual(self):
        criador = {"nivel": 3, "atributos": {"manha": 2}}
        self.assertEqual(self.motor._dificuldade_contextual(criador, self.personagem, "manha"), 16)
        criador["nivel"] = 50
        self.assertEqual(self.motor._dificuldade_contextual(criador, self.personagem, "manha"), 20)
        self.assertEqual(self.motor._dificuldade_contextual(None, self.personagem, "manha"), 12)

    def test_acoes(self):
        exemplos = [
            pedido("atacar", "golpear", alvo="rato", equipamento="machado_de_pedra"),
            pedido("atacar", "arremessar", alvo="rato", equipamento="lanca_de_graveto"),
            pedido("atacar", "sequencia", alvo="rato", equipamento="machado_de_pedra"),
            pedido("mover", "saltar", distancia=3),
            pedido("investigar", "farejar", alvo="rato"),
            pedido("outro", "encolher_se"),
            pedido("mover", "escapar"),
        ]
        for exemplo in exemplos:
            with self.subTest(acao=exemplo.acao_id):
                motor = MotorRegras(random.Random(6))
                c = cena()
                c["total_ataque_inimigo"] = 10
                resultado = motor.executar(exemplo, personagem(), c)
                self.assertEqual(resultado.status, "executado")

    def test_todas_tecnicas_possuem_despacho(self):
        for tecnica in self.motor.tecnicas:
            with self.subTest(tecnica=tecnica):
                motor = MotorRegras(random.Random(6))
                p = personagem()
                p["tecnicas_disponiveis"] = [tecnica]
                c = cena()
                c["situacao"] = "fuga"
                if tecnica.endswith("cura_dramatica"):
                    motor.aplicar_dano(p, 6)
                requisicao = pedido("usar_tecnica", tecnica=tecnica, alvo="rato" if not tecnica.endswith(("banana_curativa", "cura_mistica", "cura_dramatica")) else None, equipamento="estilingue", distancia=3, categoria="cura")
                resultado = motor.executar(requisicao, p, c)
                self.assertEqual(resultado.status, "executado", resultado.efeitos)

    def test_cena_e_descanso(self):
        self.cena.update({"objetivo": "ponte_segura", "fatos": ["ponte_segura"], "abertura_transicao": True, "dia": 1})
        self.personagem["usos_tecnicas"] = {"cena": ["teste"], "dia": ["teste"]}
        self.motor.executar(pedido(), self.personagem, self.cena)
        self.assertTrue(self.cena["encerrada"])
        self.assertEqual(self.personagem["usos_tecnicas"]["cena"], [])
        self.cena["evento_pendente"] = True
        self.motor.executar(pedido(acao="dormir"), self.personagem, self.cena)
        self.assertEqual(self.cena["dia"], 1)
        self.cena["evento_pendente"] = False
        self.motor.executar(pedido(acao="dormir"), self.personagem, self.cena)
        self.assertEqual(self.cena["dia"], 2)
        self.assertEqual(self.personagem["usos_tecnicas"]["dia"], [])

    def test_parser_repassa_cena_e_regra_sem_numeros(self):
        intent = IntentJogador(intencao="investigar", alvo=AlvoJogador(tipo="nenhum"), atributo_id="manha", dificuldade="dificil")
        with patch.dict("os.environ", {"GEMINI_API_KEY": "teste"}), patch("llm_interactive_rpg.app.pipeline.parser_ia.genai.Client") as cliente:
            cliente.return_value.models.generate_content.return_value.parsed = intent
            resposta = interpretar_acao("investigo", self.personagem, self.cena)
            self.assertEqual(resposta.dificuldade, "dificil")
            argumentos = cliente.return_value.models.generate_content.call_args.kwargs
            self.assertIn("Nunca escolha numeros de dificuldade", argumentos["config"].system_instruction)
            self.assertIn('"rato"', argumentos["config"].system_instruction)

    def test_critico_com_tecnica_duplica_duas_vezes(self):
        tecnica = "lutador_n2_porrada_com_tudo"
        self.personagem["tecnicas_disponiveis"] = [tecnica]
        self.motor.rng = DadosFixos(20)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=tecnica, alvo="rato", equipamento="machado_de_pedra"), self.personagem, self.cena)
        self.assertEqual((resultado.dano_bruto, resultado.dano_final), (16, 15))
        self.assertNotIn("machado_de_pedra", self.personagem["equipamentos"])
        self.assertIn(tecnica, self.personagem["usos_tecnicas"]["dia"])

    def test_cura_dramatica_e_limite_diario(self):
        tecnica = "curandeiro_n3_cura_dramatica"
        self.personagem["tecnicas_disponiveis"] = [tecnica]
        self.motor.aplicar_dano(self.personagem, 6)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=tecnica), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self.personagem["coracoes"]["atual"], 2)
        self.motor.aplicar_dano(self.personagem, 2)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=tecnica), self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")
        self.assertIn("caido", self.personagem["condicoes"])

    def test_paralisia_termina_por_dano_ou_turnos(self):
        self.motor._condicao(self.personagem, "paralisado", 5)
        for _ in range(4):
            resultado = self.motor.executar(pedido(), self.personagem, self.cena)
            self.assertFalse(resultado.sucesso)
            self.assertIn("paralisado", self.personagem["condicoes"])
        self.motor.executar(pedido(), self.personagem, self.cena)
        self.assertNotIn("paralisado", self.personagem["condicoes"])
        self.motor._condicao(self.personagem, "paralisado", 5)
        self.motor.aplicar_dano(self.personagem, 1)
        self.assertNotIn("paralisado", self.personagem["condicoes"])

    def test_sequencia_aplica_penalidade_por_golpe(self):
        self.motor.rng = DadosFixos(10, 10)
        resultado = self.motor.executar(pedido("atacar", "sequencia", alvo="rato", equipamento="machado_de_pedra", quantidade=2), self.personagem, self.cena)
        self.assertEqual(resultado.dano_final, 3)
        self.assertEqual(resultado.rolagem.modificador, -2)
        self.assertIn("sucesso=False", resultado.efeitos[-1])

    def test_recarga_estilingue_gigante(self):
        self.personagem["equipamentos"].append("estilingue_gigante")
        ataque = pedido("atacar", alvo="rato", equipamento="estilingue_gigante")
        self.assertEqual(self.motor.executar(ataque, self.personagem, self.cena).status, "executado")
        self.assertEqual(self.motor.executar(ataque, self.personagem, self.cena).status, "aguardando_esclarecimento")
        self.motor.executar(pedido(), self.personagem, self.cena)
        self.assertEqual(self.motor.executar(ataque, self.personagem, self.cena).status, "executado")

    def test_bolso_exige_categoria_sem_gastar_tecnica(self):
        tecnica = "catador_n1_bolso_misterioso"
        self.personagem["tecnicas_disponiveis"] = [tecnica]
        antes = deepcopy(self.personagem)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=tecnica), self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")
        self.assertEqual(self.personagem, antes)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=tecnica, categoria="cura"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self.personagem["inventario"]["banana_curativa"], 3)

    def test_regras_especificas_prevalecem(self):
        self.motor.rng = DadosFixos(10, 10)
        resultado = self.motor.executar(pedido("investigar", "farejar", alvo="rato", dificuldade="facil"), self.personagem, self.cena)
        self.assertEqual(resultado.rolagem.alvo_numero, 14)
        resultado = self.motor.executar(pedido("mover", "saltar", distancia=6, dificuldade="absurda"), self.personagem, self.cena)
        self.assertEqual(resultado.rolagem.alvo_numero, 12)

    def test_fluxo_terminal_mockado_altera_alvo(self):
        intent = IntentJogador(intencao="atacar", alvo=AlvoJogador(tipo="inimigo", id="rato"), equipamento_id="machado_de_pedra")
        self.motor.rng = DadosFixos(20)
        saida = io.StringIO()
        with (
            patch("llm_interactive_rpg.app.main.interpretar_acao", return_value=intent),
            patch("llm_interactive_rpg.app.main.narrar_resultado", return_value="O machado acerta: 7 de dano."),
            redirect_stdout(saida),
        ):
            executar_turno("ataco o rato", self.personagem, self.cena, self.motor)
        self.assertEqual(saida.getvalue().strip(), "O machado acerta: 7 de dano.")
        self.assertEqual(self.cena["inimigos"][0]["coracoes"]["atual"], 13)

    def test_objeto_da_cena_e_alvo_distintos(self):
        self.cena["objetos"] = [{"id": "pedra_01", "nome": "Pedra"}]
        self.motor.rng = DadosFixos(15)
        requisicao = pedido("atacar", "arremessar", alvo="rato")
        requisicao.parametros.objeto_id = "pedra_01"
        requisicao.parametros.tamanho_objeto = "medio"
        resultado = self.motor.executar(requisicao, self.personagem, self.cena)
        self.assertEqual(resultado.dano_bruto, 2)
        self.assertEqual(resultado.dano_final, 1)

    def test_objetivo_e_transicao_sao_verificados(self):
        self.cena.update({"objetivo": "derrotar:rato", "fatos": [], "abertura_transicao": False})
        self.cena["inimigos"][0]["coracoes"]["atual"] = 1
        self.motor.rng = DadosFixos(20)
        self.motor.executar(pedido("atacar", alvo="rato", equipamento="machado_de_pedra"), self.personagem, self.cena)
        self.assertIn("derrotar:rato", self.cena["fatos"])
        self.assertFalse(self.cena.get("encerrada", False))
        self.motor.executar(pedido(acao="encerrar_cena"), self.personagem, self.cena)
        self.assertTrue(self.cena["encerrada"])

    def test_pedido_incompleto_nao_altera_rng_ou_estado(self):
        self.personagem["inventario"]["pedra"] = 1
        antes = deepcopy((self.personagem, self.cena))
        estado_rng = self.motor.rng.getstate()
        resultado = self.motor.executar(pedido("atacar", "sequencia", alvo="rato", equipamento="estilingue", quantidade=2), self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")
        self.assertEqual((self.personagem, self.cena), antes)
        self.assertEqual(self.motor.rng.getstate(), estado_rng)

    def test_infeccao_preexistente_e_mancada_narrativa(self):
        self.motor.rng = DadosFixos(1)
        resultado = self.motor.executar(pedido(atributo="manha", dificuldade="facil"), self.personagem, self.cena)
        self.assertFalse(resultado.sucesso)
        self.assertTrue(any("Mancada" in efeito for efeito in resultado.efeitos))
        self.personagem["infeccao"]["atual"] = 5
        resultado = self.motor.executar(pedido(), self.personagem, self.cena)
        self.assertEqual(resultado.status, "bloqueado_condicao")
        self.assertTrue({"morto", "zumbi"}.issubset(self.personagem["condicoes"]))

    def test_equipar_item_obtido_no_inventario(self):
        self.personagem["inventario"]["faca_de_pedra"] = 1
        resultado = self.motor.executar(pedido(acao="equipar", equipamento="faca_de_pedra"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self.personagem["inventario"]["faca_de_pedra"], 0)
        self.assertIn("faca_de_pedra", self.personagem["equipamentos"])
        resultado = self.motor.executar(pedido(acao="equipar", equipamento="faca_de_pedra"), self.personagem, self.cena)
        self.assertEqual(resultado.status, "aguardando_esclarecimento")

    def test_bater_no_peito_e_pedrada_concedem_vantagem(self):
        bater = "lutador_n1_bater_no_peito"
        pedrada = "atirador_n1_pedrada_certeira"
        self.personagem["tecnicas_disponiveis"] = [bater, pedrada]
        self.motor.executar(pedido("usar_tecnica", tecnica=bater), self.personagem, self.cena)
        self.motor.rng = DadosFixos(1, 20)
        resultado = self.motor.executar(pedido("atacar", alvo="rato", equipamento="machado_de_pedra"), self.personagem, self.cena)
        self.assertEqual(resultado.rolagem.dados_rolados, [1, 20])
        self.assertNotIn("vantagem_ataque", self.personagem["condicoes"])
        self.motor.rng = DadosFixos(1, 15)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=pedrada, alvo="rato", equipamento="estilingue"), self.personagem, self.cena)
        self.assertEqual(resultado.rolagem.dado_escolhido, 15)
        self.assertEqual(self.personagem["inventario"]["pedra"], 2)

    def test_furia_impede_escapar_e_termina(self):
        tecnica = "lutador_n3_furia_primata"
        self.personagem["tecnicas_disponiveis"] = [tecnica]
        self.motor.executar(pedido("usar_tecnica", tecnica=tecnica), self.personagem, self.cena)
        bloqueado = self.motor.executar(pedido(acao="escapar"), self.personagem, self.cena)
        self.assertEqual(bloqueado.status, "bloqueado_condicao")
        for _ in range(3):
            self.motor.executar(pedido(), self.personagem, self.cena)
        self.assertNotIn("furia_primata", self.personagem["condicoes"])

    def test_sujeira_e_armadilha_aplicam_condicoes_distintas(self):
        sujeira = "catador_n2_sujeira_nos_olhos"
        armadilha = "catador_n3_armadilha_improvisada"
        self.personagem["tecnicas_disponiveis"] = [sujeira, armadilha]
        self.motor.rng = DadosFixos(1, 1)
        self.assertTrue(self.motor.executar(pedido("usar_tecnica", tecnica=sujeira, alvo="rato"), self.personagem, self.cena).sucesso)
        self.assertIn("cego", self.cena["inimigos"][0]["condicoes"])
        self.assertTrue(self.motor.executar(pedido("usar_tecnica", tecnica=armadilha, alvo="rato"), self.personagem, self.cena).sucesso)
        self.assertIn("derrubado", self.cena["inimigos"][0]["condicoes"])
        self.assertEqual(self.personagem["inventario"]["sucata"], 1)
        self.assertNotIn("caido", self.cena["inimigos"][0]["condicoes"])

    def test_rastrear_cipo_e_cavalgar(self):
        rastrear = "batedor_n1_rastrear"
        cipo = "batedor_n2_cipo_salvador"
        cavalgar = "batedor_n3_cavalgar_na_cabeca"
        self.personagem["tecnicas_disponiveis"] = [rastrear, cipo, cavalgar]
        self.motor.rng = DadosFixos(15, 5, 15)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=rastrear, alvo="rato"), self.personagem, self.cena)
        self.assertEqual(resultado.rolagem.alvo_numero, 13)
        self.cena["situacao"] = "queda"
        self.assertTrue(self.motor.executar(pedido("usar_tecnica", tecnica=cipo), self.personagem, self.cena).sucesso)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=cavalgar, alvo="rato"), self.personagem, self.cena)
        self.assertTrue(resultado.sucesso)
        self.assertEqual(self.personagem["montado_em"], "rato")

    def test_cha_e_curas(self):
        banana = "curandeiro_n1_banana_curativa"
        cha = "curandeiro_n2_cha_duvidoso"
        mistica = "macaco_sabio_n2_cura_mistica"
        self.personagem["tecnicas_disponiveis"] = [banana, cha, mistica]
        self.personagem["coracoes"]["atual"] = 1
        self.personagem["infeccao"]["atual"] = 2
        self.motor.rng = DadosFixos(1)
        self.motor.executar(pedido("usar_tecnica", tecnica=banana), self.personagem, self.cena)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=cha), self.personagem, self.cena)
        self.assertFalse(resultado.sucesso)
        self.assertEqual(self.personagem["infeccao"]["atual"], 1)
        self.motor.executar(pedido("usar_tecnica", tecnica=mistica, quantidade=2), self.personagem, self.cena)
        self.assertEqual(self.personagem["coracoes"]["atual"], 4)
        self.assertEqual(self.personagem["inventario"]["banana_mistica"], 6)

    def test_raio_e_olhar_fixos_consumem_bananas(self):
        raio = "macaco_sabio_n1_raio_de_banana"
        olhar = "macaco_sabio_n3_olhar_fixo"
        self.personagem["tecnicas_disponiveis"] = [raio, olhar]
        self.motor.rng = DadosFixos(15)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=raio, alvo="rato", quantidade=2), self.personagem, self.cena)
        self.assertEqual(resultado.dano_final, 1)
        self.motor.executar(pedido("usar_tecnica", tecnica=olhar, alvo="rato"), self.personagem, self.cena)
        self.assertIn("paralisado", self.cena["inimigos"][0]["condicoes"])
        self.assertEqual(self.personagem["inventario"]["banana_mistica"], 0)

    def test_arremesso_improvisado_e_salto_mortal(self):
        arremesso = "atirador_n2_arremesso_improvisado"
        salto = "atirador_n3_salto_mortal"
        self.personagem["tecnicas_disponiveis"] = [arremesso, salto]
        self.motor.rng = DadosFixos(15, 10, 20)
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=arremesso, alvo="rato", equipamento="machado_de_pedra"), self.personagem, self.cena)
        self.assertEqual(resultado.dano_final, 2)
        self.assertIn("zonzo", self.cena["inimigos"][0]["condicoes"])
        resultado = self.motor.executar(pedido("usar_tecnica", tecnica=salto, alvo="rato", equipamento="machado_de_pedra", distancia=6), self.personagem, self.cena)
        self.assertEqual(resultado.dano_bruto, 16)

    def test_personagem_compartilhado_na_cena_preserva_alteracoes(self):
        self.cena["personagem"] = self.personagem
        self.motor.rng = DadosFixos(10)
        self.motor.executar(pedido(acao="recolher_pedras"), self.personagem, self.cena)
        self.assertIs(self.cena["personagem"], self.personagem)
        self.assertEqual(self.personagem["inventario"]["pedra"], 4)


if __name__ == "__main__":
    unittest.main()
