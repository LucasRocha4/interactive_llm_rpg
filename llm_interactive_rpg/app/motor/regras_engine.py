from __future__ import annotations

import json
import random
from copy import deepcopy
from pathlib import Path
from typing import Any

from ..pipeline.schemas import PedidoMotor, ResultadoMotor, ResultadoRolagem


REGRAS_ROOT = Path(__file__).resolve().parents[2] / "app" / "regras"


class EsclarecimentoNecessario(ValueError):
    """O pedido nao contem dados suficientes para uma decisao segura."""


def _sincronizar(destino: Any, origem: Any) -> None:
    if isinstance(destino, dict) and isinstance(origem, dict):
        for chave in set(destino) - set(origem):
            del destino[chave]
        for chave, valor in origem.items():
            if chave in destino and isinstance(destino[chave], (dict, list)) and isinstance(valor, type(destino[chave])):
                _sincronizar(destino[chave], valor)
            else:
                destino[chave] = valor
    elif isinstance(destino, list) and isinstance(origem, list):
        for indice in range(min(len(destino), len(origem))):
            if isinstance(destino[indice], (dict, list)) and isinstance(origem[indice], type(destino[indice])):
                _sincronizar(destino[indice], origem[indice])
            else:
                destino[indice] = origem[indice]
        del destino[len(origem):]
        destino.extend(origem[len(destino):])


class MotorRegras:
    def __init__(self, rng: random.Random | None = None, regras_root: Path = REGRAS_ROOT):
        self.rng = rng if rng is not None else random.Random()
        self.regras_root = regras_root
        self.dificuldades = {x["id"]: x["valor"] for x in self._carregar("dificuldades")}
        self.regras = {x["id"]: x for x in self._carregar("regras_gerais")}
        self.equipamentos = {x["id"]: x for x in self._carregar("equipamentos")}
        self.acoes = {x["id"]: x for x in self._carregar("acoes")}
        self.tecnicas = {x["id"]: x for x in self._carregar("tecnicas")}
        self.efeitos = {x["id"]: x for x in self._carregar("efeitos")}
        self.tabela_itens = self._carregar("tabela_itens")

    def _carregar(self, nome: str) -> Any:
        with (self.regras_root / f"{nome}.json").open(encoding="utf-8") as arquivo:
            return json.load(arquivo)

    def obter_valor_dificuldade(self, dificuldade_id: str) -> int:
        return self.dificuldades[dificuldade_id]

    def rolar_teste(
        self, atributo_valor: int, alvo_numero: int, vantagem: bool = False,
        desvantagem: bool = False, rng: random.Random | None = None,
    ) -> ResultadoRolagem:
        gerador = rng if rng is not None else self.rng
        dados = [gerador.randint(1, 20) for _ in range(2 if vantagem != desvantagem else 1)]
        escolhido = max(dados) if vantagem and not desvantagem else min(dados)
        return ResultadoRolagem(
            executada=True, dados_rolados=dados, dado_escolhido=escolhido,
            modificador=atributo_valor, total=escolhido + atributo_valor,
            alvo_numero=alvo_numero, critico=escolhido == 20, mancada=escolhido == 1,
        )

    @staticmethod
    def _sucesso(rolagem: ResultadoRolagem) -> bool:
        assert rolagem.total is not None and rolagem.alvo_numero is not None
        return rolagem.critico or (not rolagem.mancada and rolagem.total >= rolagem.alvo_numero)

    @staticmethod
    def calcular_dano(dano_base: int, protecao_alvo: int, critico: bool = False) -> tuple[int, int, int]:
        if dano_base < 0 or protecao_alvo < 0:
            raise ValueError("Dano e protecao devem ser nao negativos.")
        bruto = dano_base * (2 if critico else 1)
        return bruto, min(bruto, protecao_alvo), max(0, bruto - protecao_alvo)

    def aplicar_dano(self, personagem: dict[str, Any], dano_final: int) -> list[str]:
        if dano_final < 0:
            raise ValueError("Dano nao pode ser negativo.")
        coracoes = personagem["coracoes"]
        anterior = coracoes["atual"]
        coracoes["atual"] = max(0, anterior - dano_final)
        alteracoes = [f"coracoes: {anterior} -> {coracoes['atual']}"]
        if dano_final > 0 and "paralisado" in personagem.get("condicoes", []):
            self._remover_condicao(personagem, "paralisado")
            alteracoes.append("paralisado removido por dano")
        if anterior > 0 and coracoes["atual"] == 0:
            condicoes = personagem.setdefault("condicoes", [])
            if "caido" not in condicoes:
                condicoes.append("caido")
            personagem["turnos_caido"] = 0
            alteracoes.append("condicao: caido")
        return alteracoes

    def aplicar_infeccao(self, personagem: dict[str, Any], pontos: int) -> list[str]:
        infeccao = personagem["infeccao"]
        anterior = infeccao["atual"]
        limite = self.regras["infeccao"]["valores"]["maximo"]
        infeccao["atual"] = max(0, min(limite, anterior + pontos))
        alteracoes = [f"infeccao: {anterior} -> {infeccao['atual']}"]
        if infeccao["atual"] >= limite:
            condicoes = personagem.setdefault("condicoes", [])
            for condicao in ("morto", "zumbi"):
                if condicao not in condicoes:
                    condicoes.append(condicao)
                    alteracoes.append(f"condicao: {condicao}")
        return alteracoes

    @staticmethod
    def _remover_condicao(personagem: dict[str, Any], condicao: str) -> None:
        if condicao in personagem.get("condicoes", []):
            personagem["condicoes"].remove(condicao)
        personagem.get("duracoes", {}).pop(condicao, None)

    def _condicao(self, personagem: dict[str, Any], condicao: str, duracao: int | None = None) -> None:
        condicoes = personagem.setdefault("condicoes", [])
        if condicao not in condicoes:
            condicoes.append(condicao)
        if duracao is None and condicao in self.efeitos:
            duracao_catalogo = self.efeitos[condicao]["duracao_turnos"]
            if duracao_catalogo is not None:
                duracao = duracao_catalogo + 1
        if duracao is not None:
            personagem.setdefault("duracoes", {})[condicao] = duracao

    @staticmethod
    def _atributo(personagem: dict[str, Any], nome: str) -> int:
        valor = personagem.get("atributos", {}).get(nome)
        if not isinstance(valor, int) or isinstance(valor, bool):
            raise EsclarecimentoNecessario(f"Atributo {nome} ausente ou invalido.")
        return valor

    @staticmethod
    def _inventario(personagem: dict[str, Any]) -> dict[str, int]:
        inventario = personagem.get("inventario")
        if not isinstance(inventario, dict):
            raise EsclarecimentoNecessario("Inventario com quantidades ausente.")
        return inventario

    def _consumir(self, personagem: dict[str, Any], item: str, quantidade: int = 1) -> None:
        inventario = self._inventario(personagem)
        if not isinstance(inventario.get(item, 0), int) or inventario.get(item, 0) < quantidade:
            raise EsclarecimentoNecessario(f"Quantidade insuficiente de {item}.")
        inventario[item] -= quantidade

    def _curar(self, personagem: dict[str, Any], quantidade: int) -> list[str]:
        if "morto" in personagem.get("condicoes", []):
            raise EsclarecimentoNecessario("Personagem morto nao pode ser curado.")
        coracoes = personagem["coracoes"]
        anterior = coracoes["atual"]
        coracoes["atual"] = min(coracoes["maximo"], anterior + quantidade)
        if coracoes["atual"] > 0:
            self._remover_condicao(personagem, "caido")
            personagem["turnos_caido"] = 0
        return [f"coracoes: {anterior} -> {coracoes['atual']}"]

    def verificar_e_processar_condicoes(
        self, personagem: dict[str, Any], pedido: PedidoMotor, rng: random.Random | None = None,
    ) -> ResultadoMotor | None:
        condicoes = personagem.get("condicoes", [])
        if "morto" in condicoes:
            return ResultadoMotor(status="bloqueado_condicao", efeitos=["Personagem morto nao pode agir."])
        if "paralisado" in condicoes:
            return ResultadoMotor(status="executado", sucesso=False, efeitos=["Turno perdido: personagem paralisado nao pode agir."])
        if "caido" not in condicoes and "derrubado" not in condicoes:
            return None
        if pedido.tecnica_id == "curandeiro_n3_cura_dramatica" and "caido" in condicoes:
            return None
        if pedido.tipo == "usar_item" and pedido.parametros.equipamento_id == "banana_curativa":
            self._consumir(personagem, "banana_curativa")
            alteracoes = self._curar(personagem, 1)
            return ResultadoMotor(status="executado", sucesso=True, alteracoes_personagem=alteracoes, efeitos=["Banana curativa consumida."])
        if pedido.acao_id != "levantar":
            return ResultadoMotor(status="bloqueado_condicao", efeitos=["Somente levantar ou curar enquanto caido ou derrubado."])
        if "caido" not in condicoes:
            self._remover_condicao(personagem, "derrubado")
            return ResultadoMotor(status="executado", sucesso=True, efeitos=["Personagem levantou."])
        regra = self.regras["caido_solo"]["valores"]
        rolagem = self.rolar_teste(self._atributo(personagem, "acaso"), regra["dificuldade"], pedido.teste.vantagem, pedido.teste.desvantagem, rng)
        sucesso = self._sucesso(rolagem)
        alteracoes = []
        if sucesso:
            alteracoes.extend(self._curar(personagem, regra["coracoes_para_levantar"]))
        else:
            personagem["turnos_caido"] = personagem.get("turnos_caido", 0) + 1
            alteracoes.append(f"turnos_caido: {personagem['turnos_caido']}")
            if personagem["turnos_caido"] >= regra["turnos"]:
                self._condicao(personagem, "morto")
                alteracoes.append("condicao: morto")
        return ResultadoMotor(status="executado", sucesso=sucesso, rolagem=rolagem, alteracoes_personagem=alteracoes)

    def _alvo(self, pedido: PedidoMotor, personagem: dict[str, Any], cena: dict[str, Any]) -> dict[str, Any]:
        alvo_id = pedido.parametros.alvo_id
        if alvo_id == personagem.get("id") or alvo_id == "proprio":
            return personagem
        for grupo in ("inimigos", "npcs"):
            for alvo in cena.get(grupo, []):
                if alvo.get("id") == alvo_id and alvo_id is not None:
                    return alvo
        raise EsclarecimentoNecessario("Alvo inexistente ou nao informado.")

    @staticmethod
    def _defesa(alvo: dict[str, Any]) -> int:
        defesa = alvo.get("defesa")
        if defesa is None and alvo.get("tipo") == "macaco":
            defesa = 10 + MotorRegras._atributo(alvo, "pulo")
        if not isinstance(defesa, int):
            raise EsclarecimentoNecessario("Defesa do alvo nao informada.")
        return defesa

    def _teste(self, personagem: dict[str, Any], pedido: PedidoMotor, atributo: str, alvo: int, *, vantagem: bool = False, desvantagem: bool = False, penalidade: int = 0) -> ResultadoRolagem:
        return self.rolar_teste(
            self._atributo(personagem, atributo) + penalidade, alvo,
            pedido.teste.vantagem or vantagem,
            pedido.teste.desvantagem or desvantagem or "zonzo" in personagem.get("condicoes", []),
        )

    def _ataque(
        self, pedido: PedidoMotor, personagem: dict[str, Any], cena: dict[str, Any],
        *, dano_especial: int | None = None, multiplicador: int = 1,
        vantagem: bool = False, exigir_estilingue: bool = False, magico: bool = False,
        objeto_improvisado: bool = False, atributo_forcado: str | None = None,
    ) -> ResultadoMotor:
        alvo = self._alvo(pedido, personagem, cena)
        defesa = self._defesa(alvo)
        protecao = alvo.get("protecao")
        if protecao is None and (alvo is personagem or alvo.get("tipo") == "macaco"):
            protecao = sum(
                self.equipamentos.get(item, {}).get("protecao") or 0
                for item in alvo.get("equipamentos", [])
            )
        if isinstance(protecao, int):
            protecao += alvo.get("protecao_temporaria", 0)
        if not isinstance(protecao, int) or protecao < 0 or "coracoes" not in alvo:
            raise EsclarecimentoNecessario("Protecao ou coracoes do alvo ausentes.")
        arma_id = None if magico else (pedido.parametros.objeto_id or pedido.parametros.equipamento_id)
        arma = self.equipamentos.get(arma_id or "")
        arremesso = pedido.acao_id == "arremessar"
        objeto = next((x for x in cena.get("objetos", []) if x.get("id") == arma_id), None)
        possui_objeto = bool(
            arma_id and (
                arma_id in personagem.get("equipamentos", [])
                or personagem.get("inventario", {}).get(arma_id, 0) > 0
                or objeto
            )
        )
        if objeto_improvisado and not possui_objeto:
            raise EsclarecimentoNecessario("Objeto para a tecnica nao informado ou indisponivel.")
        if dano_especial is None:
            possui_arma = arma and arma_id in personagem.get("equipamentos", [])
            if not possui_arma and not ((arremesso or objeto_improvisado) and possui_objeto):
                raise EsclarecimentoNecessario("Arma equipada ou objeto da cena nao informado.")
            if possui_arma and arremesso and not arma.get("arremessavel"):
                raise EsclarecimentoNecessario("Esta arma nao e arremessavel.")
            if possui_arma and isinstance(arma.get("dano"), int):
                dano_especial = arma["dano"]
            else:
                tamanhos = self.acoes["arremessar"]["efeitos"]["dano_por_tamanho"]
                tamanho = pedido.parametros.tamanho_objeto
                if tamanho not in tamanhos:
                    raise EsclarecimentoNecessario("Tamanho do objeto deve ser pequeno, medio ou pesado.")
                dano_especial = tamanhos[tamanho]
        if exigir_estilingue and (not arma_id or not arma_id.startswith("estilingue")):
            raise EsclarecimentoNecessario("A tecnica exige um estilingue equipado.")
        if not objeto_improvisado and arma_id and personagem.get("recargas", {}).get(arma_id, 0) > 0:
            raise EsclarecimentoNecessario("A arma ainda esta recarregando.")
        if not objeto_improvisado and arma_id and arma_id.startswith("estilingue"):
            if not arma or arma_id not in personagem.get("equipamentos", []):
                raise EsclarecimentoNecessario("Estilingue nao equipado.")
            self._consumir(personagem, "pedra")
        if not objeto_improvisado and arma and arma.get("recarga_turnos"):
            personagem.setdefault("recargas", {})[arma_id] = arma["recarga_turnos"] + 1
        atributo = "pulo" if magico or arremesso or (not objeto_improvisado and ((arma and arma.get("a_distancia")) or arma is None)) else "garra"
        if atributo_forcado:
            atributo = atributo_forcado
        condicoes = personagem.get("condicoes", [])
        vantagem = vantagem or "vantagem_ataque" in condicoes or "furia_primata" in condicoes or personagem.get("vantagem_alvo") == alvo.get("id")
        ataques = personagem.get("ataques_no_turno", 0)
        rolagem = self._teste(personagem, pedido, atributo, defesa, vantagem=vantagem, desvantagem="cego" in condicoes, penalidade=-5 * ataques)
        personagem["ataques_no_turno"] = ataques + 1
        self._remover_condicao(personagem, "vantagem_ataque")
        sucesso = self._sucesso(rolagem)
        bruto = aplicado = final = 0
        alteracoes = []
        if sucesso:
            bruto, aplicado, final = self.calcular_dano(dano_especial * multiplicador, protecao, rolagem.critico)
            alteracoes = self.aplicar_dano(alvo, final)
            if alvo["coracoes"]["atual"] == 0 and alvo in cena.get("inimigos", []):
                fato = f"derrotar:{alvo['id']}"
                fatos = cena.setdefault("fatos", [])
                if fato not in fatos:
                    fatos.append(fato)
        efeitos = ["Mancada: o narrador descreve um efeito comico."] if rolagem.mancada else []
        return ResultadoMotor(status="executado", sucesso=sucesso, rolagem=rolagem, dano_bruto=bruto, protecao_aplicada=aplicado, dano_final=final, efeitos=efeitos, alteracoes_personagem=alteracoes)

    def _dificuldade_contextual(self, criador: dict[str, Any] | None, executor: dict[str, Any], atributo: str) -> int:
        if criador is None:
            return 12
        nivel = criador.get("nivel")
        nivel_executor = executor.get("nivel")
        habilidade = criador.get("atributos", {}).get(atributo)
        if not all(isinstance(valor, int) for valor in (nivel, nivel_executor, habilidade)):
            return 12
        return max(8, min(20, 12 + habilidade + nivel - nivel_executor))

    def _acao(self, pedido: PedidoMotor, personagem: dict[str, Any], cena: dict[str, Any]) -> ResultadoMotor:
        acao = pedido.acao_id
        if acao == "sequencia":
            quantidade = pedido.parametros.quantidade or 1
            resultados = [self._ataque(pedido, personagem, cena) for _ in range(quantidade)]
            ultimo = resultados[-1]
            efeitos = [f"Golpe {i}: total {item.rolagem.total}, sucesso={item.sucesso}" for i, item in enumerate(resultados, 1) if item.rolagem]
            ultimo.sucesso = any(item.sucesso for item in resultados)
            ultimo.dano_bruto = sum(item.dano_bruto for item in resultados)
            ultimo.protecao_aplicada = sum(item.protecao_aplicada for item in resultados)
            ultimo.dano_final = sum(item.dano_final for item in resultados)
            ultimo.efeitos = efeitos
            ultimo.alteracoes_personagem = [alteracao for item in resultados for alteracao in item.alteracoes_personagem]
            return ultimo
        if pedido.tipo == "atacar" or acao in ("golpear", "arremessar"):
            return self._ataque(pedido, personagem, cena)
        if acao == "recolher_pedras":
            inventario = self._inventario(personagem)
            rolagem = self._teste(personagem, pedido, "manha", self.obter_valor_dificuldade("facil"))
            sucesso = self._sucesso(rolagem)
            if sucesso:
                inventario["pedra"] = inventario.get("pedra", 0) + 1
            return ResultadoMotor(status="executado", sucesso=sucesso, rolagem=rolagem, alteracoes_personagem=["pedra: +1"] if sucesso else [])
        if acao == "equipar":
            item = pedido.parametros.equipamento_id
            equipamento = self.equipamentos.get(item or "")
            if not equipamento or equipamento["categoria"] not in ("arma", "protecao"):
                raise EsclarecimentoNecessario("Informe uma arma ou protecao para equipar.")
            if item in personagem.get("equipamentos", []):
                raise EsclarecimentoNecessario("Equipamento ja utilizado.")
            self._consumir(personagem, item)
            personagem.setdefault("equipamentos", []).append(item)
            return ResultadoMotor(status="executado", sucesso=True, alteracoes_personagem=[f"{item} equipado."])
        if acao == "levantar":
            raise EsclarecimentoNecessario("O personagem nao esta caido.")
        if pedido.tipo == "usar_item":
            if pedido.parametros.equipamento_id != "banana_curativa":
                raise EsclarecimentoNecessario("Item sem efeito implementado ou nao informado.")
            self._consumir(personagem, "banana_curativa")
            return ResultadoMotor(status="executado", sucesso=True, alteracoes_personagem=self._curar(personagem, 1))
        if acao == "encolher_se":
            escudo = any("escudo" in item for item in personagem.get("equipamentos", []))
            personagem["protecao_temporaria"] = 2 if escudo else 1
            personagem["perder_proximo_turno"] = True
            return ResultadoMotor(status="executado", sucesso=True, efeitos=["Protecao temporaria; proximo turno perdido."])
        if acao == "escapar":
            if "furia_primata" in personagem.get("condicoes", []):
                return ResultadoMotor(status="bloqueado_condicao", efeitos=["Furia Primata impede escapar."])
            total = cena.get("total_ataque_inimigo")
            if not isinstance(total, int):
                raise EsclarecimentoNecessario("Total do ataque inimigo nao informado.")
            rolagem = self._teste(personagem, pedido, "pulo", total + 1)
            return ResultadoMotor(status="executado", sucesso=self._sucesso(rolagem), rolagem=rolagem)
        if acao == "saltar":
            entidades = cena.get("inimigos", []) + cena.get("npcs", [])
            if any(entidade.get("id") == pedido.parametros.alvo_id for entidade in entidades):
                alvo = self._alvo(pedido, personagem, cena)
                if alvo.get("tamanho") not in ("grande", "maior", "gigante"):
                    raise EsclarecimentoNecessario("Montar exige alvo maior com tamanho informado.")
                atributo_alvo = self._atributo(alvo, "pulo")
                defesa = self.rolar_teste(atributo_alvo, 0)
                assert defesa.total is not None
                rolagem = self._teste(personagem, pedido, "pulo", defesa.total + 1)
                sucesso = self._sucesso(rolagem)
                if sucesso:
                    personagem["vantagem_alvo"] = alvo["id"]
                    personagem["montado_em"] = alvo["id"]
                return ResultadoMotor(status="executado", sucesso=sucesso, rolagem=rolagem, efeitos=[f"Defensor: {defesa.total}"])
            if pedido.parametros.alvo_id and not any(
                local.get("id") == pedido.parametros.alvo_id for local in cena.get("locais", [])
            ):
                raise EsclarecimentoNecessario("Destino do salto nao encontrado na cena.")
            distancia = pedido.parametros.distancia_m
            if distancia is None or distancia > 9:
                raise EsclarecimentoNecessario("Distancia do salto deve ser informada e nao exceder 9 m.")
            dificuldade = 8 if distancia <= 3 else 12 if distancia <= 6 else 16
            rolagem = self._teste(personagem, pedido, "pulo", dificuldade)
            return ResultadoMotor(status="executado", sucesso=self._sucesso(rolagem), rolagem=rolagem)
        if acao == "farejar":
            alvo = self._alvo(pedido, personagem, cena)
            rolagem = self._teste(personagem, pedido, "manha", self.acoes["farejar"]["teste"]["dificuldade"])
            sucesso = self._sucesso(rolagem)
            if sucesso:
                personagem["vantagem_alvo"] = alvo["id"]
            return ResultadoMotor(status="executado", sucesso=sucesso, rolagem=rolagem)
        if acao == "dormir":
            if cena.get("evento_pendente"):
                return ResultadoMotor(status="executado", sucesso=False, efeitos=["Descanso interrompido por evento pendente."])
            cena["dia"] = cena.get("dia", 1) + 1
            personagem.setdefault("usos_tecnicas", {})["dia"] = []
            return ResultadoMotor(status="executado", sucesso=True, efeitos=["Descanso concluido; novo dia."])
        if acao == "encerrar_cena":
            objetivo = cena.get("objetivo")
            if not objetivo or objetivo not in cena.get("fatos", []):
                raise EsclarecimentoNecessario("O objetivo da cena ainda nao foi concluido.")
            cena["abertura_transicao"] = True
            return ResultadoMotor(status="executado", sucesso=True, efeitos=["Abertura para transicao registrada."])
        if pedido.teste.atributo_id:
            if not pedido.teste.dificuldade:
                raise EsclarecimentoNecessario("Dificuldade qualitativa nao informada.")
            rolagem = self._teste(personagem, pedido, pedido.teste.atributo_id, self.obter_valor_dificuldade(pedido.teste.dificuldade))
            return ResultadoMotor(status="executado", sucesso=self._sucesso(rolagem), rolagem=rolagem)
        if acao is not None:
            raise EsclarecimentoNecessario(f"Acao desconhecida ou sem dados suficientes: {acao}.")
        alvo_id = pedido.parametros.alvo_id
        if alvo_id and alvo_id != personagem.get("id") and not any(
            item.get("id") == alvo_id
            for grupo in ("inimigos", "npcs", "objetos", "locais")
            for item in cena.get(grupo, [])
        ):
            raise EsclarecimentoNecessario("Alvo nao encontrado na cena.")
        return ResultadoMotor(status="executado", sucesso=True, efeitos=["Acao sem teste mecanico."])

    def _tecnica(self, pedido: PedidoMotor, personagem: dict[str, Any], cena: dict[str, Any]) -> ResultadoMotor:
        tecnica_id = pedido.tecnica_id
        if not tecnica_id or tecnica_id not in self.tecnicas:
            raise EsclarecimentoNecessario("Tecnica desconhecida.")
        if tecnica_id not in personagem.get("tecnicas_disponiveis", []):
            raise EsclarecimentoNecessario("Tecnica nao disponivel para o personagem.")
        tecnica = self.tecnicas[tecnica_id]
        frequencia = tecnica["frequencia"]
        usos = personagem.setdefault("usos_tecnicas", {})
        usada = frequencia in ("cena", "dia") and tecnica_id in usos.get(frequencia, [])
        if usada and not tecnica_id.endswith("arremesso_improvisado"):
            raise EsclarecimentoNecessario(f"Tecnica ja utilizada neste periodo: {frequencia}.")
        nome = tecnica_id.split("_n", 1)[1].split("_", 1)[1]
        resultado: ResultadoMotor
        if nome == "bater_no_peito":
            self._condicao(personagem, "vantagem_ataque")
            resultado = ResultadoMotor(status="executado", sucesso=True, efeitos=["Vantagem no proximo ataque."])
        elif nome == "furia_primata":
            self._condicao(personagem, "furia_primata", 4)
            resultado = ResultadoMotor(status="executado", sucesso=True, efeitos=["Furia Primata por tres turnos."])
        elif nome in ("pedrada_certeira", "salto_mortal", "porrada_com_tudo", "arremesso_improvisado"):
            if nome == "salto_mortal" and (pedido.parametros.distancia_m is None or pedido.parametros.distancia_m > 6):
                raise EsclarecimentoNecessario("Salto Mortal exige distancia de ate 6 m.")
            resultado = self._ataque(
                pedido, personagem, cena, dano_especial=3 if nome == "arremesso_improvisado" else None,
                multiplicador=2 if nome in ("salto_mortal", "porrada_com_tudo") else 1,
                vantagem=nome in ("pedrada_certeira", "salto_mortal"),
                exigir_estilingue=nome == "pedrada_certeira",
                objeto_improvisado=nome in ("porrada_com_tudo", "arremesso_improvisado"),
                atributo_forcado="pulo" if nome == "arremesso_improvisado" else None,
            )
            if nome == "porrada_com_tudo":
                item = pedido.parametros.objeto_id or pedido.parametros.equipamento_id
                if item in personagem.get("equipamentos", []):
                    personagem["equipamentos"].remove(item)
                elif personagem.get("inventario", {}).get(item, 0) > 0:
                    self._consumir(personagem, item)
                else:
                    cena["objetos"] = [objeto for objeto in cena.get("objetos", []) if objeto.get("id") != item]
                resultado.efeitos.append("Objeto utilizado quebrou.")
            if nome == "arremesso_improvisado" and resultado.sucesso and not usada:
                self._condicao(self._alvo(pedido, personagem, cena), "zonzo")
        elif nome == "bolso_misterioso":
            categoria = pedido.parametros.categoria_item
            itens = self.tabela_itens.get(categoria or "")
            if not itens:
                raise EsclarecimentoNecessario("Categoria de item util nao informada ou sem itens.")
            inventario = self._inventario(personagem)
            item = self.rng.choice(itens)
            inventario[item] = inventario.get(item, 0) + 1
            resultado = ResultadoMotor(status="executado", sucesso=True, alteracoes_personagem=[f"{item}: +1"])
        elif nome in ("sujeira_nos_olhos", "armadilha_improvisada"):
            alvo = self._alvo(pedido, personagem, cena)
            atributo = self._atributo(alvo, "acaso")
            dificuldade = self._dificuldade_contextual(personagem, alvo, "manha")
            if nome == "armadilha_improvisada":
                self._consumir(personagem, "sucata")
            rolagem = self.rolar_teste(atributo, dificuldade)
            sucesso = not self._sucesso(rolagem)
            if sucesso:
                self._condicao(alvo, "cego" if nome == "sujeira_nos_olhos" else "derrubado")
            resultado = ResultadoMotor(status="executado", sucesso=sucesso, rolagem=rolagem)
        elif nome == "rastrear":
            alvo = self._alvo(pedido, personagem, cena)
            dificuldade = self._dificuldade_contextual(alvo, personagem, "manha")
            rolagem = self._teste(personagem, pedido, "manha", dificuldade)
            resultado = ResultadoMotor(status="executado", sucesso=self._sucesso(rolagem), rolagem=rolagem)
        elif nome == "cipo_salvador":
            if cena.get("situacao") not in ("fuga", "queda"):
                raise EsclarecimentoNecessario("Cipo Salvador exige uma situacao de fuga ou queda.")
            resultado = ResultadoMotor(status="executado", sucesso=True, efeitos=["Fuga ou queda resolvida automaticamente."])
        elif nome == "cavalgar_na_cabeca":
            resultado = self._acao(pedido.model_copy(update={"acao_id": "saltar", "tipo": "mover"}), personagem, cena)
        elif nome in ("banana_curativa", "cura_mistica", "cura_dramatica"):
            alvo = personagem if nome == "cura_dramatica" or not pedido.parametros.alvo_id else self._alvo(pedido, personagem, cena)
            if alvo is not personagem and alvo not in cena.get("npcs", []):
                raise EsclarecimentoNecessario("Cura exige o proprio personagem ou um NPC aliado.")
            if nome == "cura_dramatica" and "caido" not in personagem.get("condicoes", []):
                raise EsclarecimentoNecessario("Cura Dramatica exige personagem caido.")
            quantidade = pedido.parametros.quantidade or 1
            if nome == "cura_mistica":
                self._consumir(personagem, "banana_mistica", quantidade)
            else:
                quantidade = 2 if nome == "cura_dramatica" else 1
            resultado = ResultadoMotor(status="executado", sucesso=True, alteracoes_personagem=self._curar(alvo, quantidade))
        elif nome == "cha_duvidoso":
            if "infeccao" not in personagem:
                raise EsclarecimentoNecessario("Infeccao do personagem nao informada.")
            dificuldade = self._dificuldade_contextual(None, personagem, "acaso")
            rolagem = self._teste(personagem, pedido, "acaso", dificuldade)
            alteracoes = self.aplicar_infeccao(personagem, -1)
            resultado = ResultadoMotor(status="executado", sucesso=self._sucesso(rolagem), rolagem=rolagem, alteracoes_personagem=alteracoes, efeitos=[] if self._sucesso(rolagem) else ["Efeito colateral comico para o narrador."])
        elif nome in ("raio_de_banana", "olhar_fixo"):
            quantidade = 6 if nome == "olhar_fixo" else pedido.parametros.quantidade or 1
            alvo = self._alvo(pedido, personagem, cena)
            if nome == "raio_de_banana":
                resultado = self._ataque(pedido, personagem, cena, dano_especial=quantidade, magico=True)
            else:
                self._condicao(alvo, "paralisado")
                resultado = ResultadoMotor(status="executado", sucesso=True, efeitos=["Alvo paralisado por cinco turnos ou ate sofrer dano."])
            self._consumir(personagem, "banana_mistica", quantidade)
        else:
            raise EsclarecimentoNecessario(f"Tecnica sem implementacao: {tecnica_id}.")
        if resultado.status == "executado" and frequencia in ("cena", "dia") and not usada and (nome != "arremesso_improvisado" or resultado.sucesso):
            usos.setdefault(frequencia, []).append(tecnica_id)
        return resultado

    def _avancar(self, personagem: dict[str, Any], cena: dict[str, Any]) -> None:
        cena["turno"] = cena.get("turno", 0) + 1
        personagem["ataques_no_turno"] = 0
        for arma, restante in list(personagem.get("recargas", {}).items()):
            personagem["recargas"][arma] = max(0, restante - 1)
        entidades = [personagem] + cena.get("inimigos", []) + cena.get("npcs", [])
        processados: set[int] = set()
        for entidade in entidades:
            if id(entidade) in processados:
                continue
            processados.add(id(entidade))
            for condicao, duracao in list(entidade.get("duracoes", {}).items()):
                entidade["duracoes"][condicao] = duracao - 1
                if duracao <= 1:
                    self._remover_condicao(entidade, condicao)
        objetivo = cena.get("objetivo")
        fatos = cena.get("fatos", [])
        if not cena.get("encerrada") and objetivo and objetivo in fatos and cena.get("abertura_transicao"):
            cena["encerrada"] = True
            personagem.setdefault("usos_tecnicas", {})["cena"] = []

    def executar(self, pedido: PedidoMotor, personagem: dict[str, Any], contexto_cena: dict[str, Any] | None = None) -> ResultadoMotor:
        if pedido.perguntas_pendentes:
            return ResultadoMotor(status="aguardando_esclarecimento", efeitos=pedido.perguntas_pendentes)
        cena_original = contexto_cena if contexto_cena is not None else {}
        personagem_copia, cena = deepcopy((personagem, cena_original))
        estado_rng = self.rng.getstate()
        try:
            if personagem_copia.get("infeccao", {}).get("atual", 0) >= self.regras["infeccao"]["valores"]["maximo"]:
                self.aplicar_infeccao(personagem_copia, 0)
            resultado = self.verificar_e_processar_condicoes(personagem_copia, pedido)
            if resultado is None:
                if personagem_copia.get("perder_proximo_turno"):
                    personagem_copia["perder_proximo_turno"] = False
                    personagem_copia["protecao_temporaria"] = 0
                    resultado = ResultadoMotor(status="executado", sucesso=False, efeitos=["Turno perdido apos encolher-se."])
                elif pedido.tipo == "usar_tecnica":
                    resultado = self._tecnica(pedido, personagem_copia, cena)
                else:
                    resultado = self._acao(pedido, personagem_copia, cena)
            if resultado.status == "executado":
                if resultado.rolagem and resultado.rolagem.mancada and not any("Mancada" in efeito for efeito in resultado.efeitos):
                    resultado.efeitos.append("Mancada: o narrador descreve um efeito comico.")
                self._avancar(personagem_copia, cena)
                _sincronizar(personagem, personagem_copia)
                _sincronizar(cena_original, cena)
            elif "morto" in personagem_copia.get("condicoes", []) and "morto" not in personagem.get("condicoes", []):
                _sincronizar(personagem, personagem_copia)
            return resultado
        except EsclarecimentoNecessario as erro:
            self.rng.setstate(estado_rng)
            return ResultadoMotor(status="aguardando_esclarecimento", efeitos=[str(erro)])
