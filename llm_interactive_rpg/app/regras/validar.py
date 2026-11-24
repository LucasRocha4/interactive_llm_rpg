"""Valida o banco JSON extraído do PDF do Sistema d20 do Macaco."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parent
COLLECTIONS = (
    "atributos",
    "pelagens",
    "oficios",
    "tecnicas",
    "defeitos",
    "equipamentos",
    "kits",
    "acoes",
    "dificuldades",
    "regras_gerais",
    "exemplos_de_ficha",
)


def load(name: str) -> Any:
    with (ROOT / f"{name}.json").open(encoding="utf-8") as file:
        return json.load(file)


def fail(message: str) -> None:
    raise ValueError(message)


def validate() -> dict[str, int]:
    data = {name: load(name) for name in COLLECTIONS}
    schema = load("schema")
    errors = sorted(Draft202012Validator(schema).iter_errors(data), key=lambda error: list(error.path))
    if errors:
        fail("schema: " + "; ".join(error.message for error in errors))

    ids: dict[str, str] = {}
    for collection, records in data.items():
        if not isinstance(records, list):
            fail(f"{collection}: deve ser uma lista")
        for record in records:
            record_id = record["id"]
            if record_id in ids:
                fail(f"id repetido: {record_id} ({ids[record_id]} e {collection})")
            ids[record_id] = collection
            if not record["texto_original"].strip():
                fail(f"{collection}/{record_id}: texto_original vazio")

    def reference(record_id: str, collection: str, where: str) -> None:
        if ids.get(record_id) != collection:
            fail(f"{where}: referência inválida {record_id!r}; esperado em {collection}")

    if len(data["atributos"]) != 4:
        fail("esperados 4 atributos")
    if len(data["pelagens"]) != 6:
        fail("esperadas 6 pelagens")
    for pelagem in data["pelagens"]:
        values = pelagem["atributos"]
        if sum(values.values()) != 6 or any(value not in (1, 2) for value in values.values()):
            fail(f"{pelagem['id']}: pelagem não soma 6 com valores 1 ou 2")

    if len(data["dificuldades"]) != 4 or {item["valor"] for item in data["dificuldades"]} != {8, 12, 16, 20}:
        fail("dificuldades devem ser exatamente 8, 12, 16 e 20")
    if len(data["oficios"]) != 6:
        fail("esperados 6 ofícios")
    bonus_pairs = set()
    for oficio in data["oficios"]:
        bonuses = oficio["bonus_atributos"]
        if len(bonuses) != 2 or len({bonus["atributo_id"] for bonus in bonuses}) != 2:
            fail(f"{oficio['id']}: deve ter dois bônus em atributos diferentes")
        for bonus in bonuses:
            reference(bonus["atributo_id"], "atributos", f"{oficio['id']}.bonus_atributos")
        pair = tuple(sorted(bonus["atributo_id"] for bonus in bonuses))
        if pair in bonus_pairs:
            fail(f"par de bônus repetido: {pair}")
        bonus_pairs.add(pair)
        initial = oficio["equipamento_inicial"]
        if "coluna" in initial and initial["coluna"] not in {"leve", "pesado", "atirador"}:
            fail(f"{oficio['id']}: coluna inválida")
        for item in initial.get("itens", []):
            reference(item["equipamento_id"], "equipamentos", f"{oficio['id']}.equipamento_inicial")

    if len(data["tecnicas"]) != 18:
        fail("esperadas 18 técnicas")
    levels: dict[str, set[int]] = {}
    for technique in data["tecnicas"]:
        reference(technique["oficio_id"], "oficios", f"{technique['id']}.oficio_id")
        levels.setdefault(technique["oficio_id"], set()).add(technique["nivel"])
    if any(values != {1, 2, 3} for values in levels.values()) or len(levels) != 6:
        fail("cada ofício deve ter técnicas de níveis 1, 2 e 3")

    if len(data["defeitos"]) != 6:
        fail("esperados 6 defeitos")
    if len(data["kits"]) != 18:
        fail("esperados 18 kits")
    by_column: dict[str, set[int]] = {}
    for kit in data["kits"]:
        by_column.setdefault(kit["coluna"], set()).add(kit["numero"])
        for item in kit["itens"]:
            reference(item["equipamento_id"], "equipamentos", f"{kit['id']}.itens")
    if by_column != {"leve": set(range(1, 7)), "pesado": set(range(1, 7)), "atirador": set(range(1, 7))}:
        fail("kits devem ter números 1 a 6 em cada coluna")

    expected_actions = {"Golpear", "Escapar", "Saltar", "Arremessar", "Farejar", "Encolher-se", "Sequência"}
    if len(data["acoes"]) != 7 or {action["nome"] for action in data["acoes"]} != expected_actions:
        fail("ações não correspondem às 7 ações do PDF")

    for pelagem in data["pelagens"]:
        for oficio in data["oficios"]:
            values = dict(pelagem["atributos"])
            for bonus in oficio["bonus_atributos"]:
                values[bonus["atributo_id"]] += bonus["valor"]
            if any(value < 1 or value > 3 for value in values.values()):
                fail(f"combinação inválida: {pelagem['id']} + {oficio['id']}")

    if len(data["exemplos_de_ficha"]) != 1:
        fail("esperada uma ficha de exemplo")
    example = data["exemplos_de_ficha"][0]
    reference(example["escolhas"]["pelagem_id"], "pelagens", "exemplo.escolhas.pelagem_id")
    reference(example["escolhas"]["oficio_id"], "oficios", "exemplo.escolhas.oficio_id")
    reference(example["escolhas"]["defeito_id"], "defeitos", "exemplo.escolhas.defeito_id")
    reference(example["escolhas"]["equipamento_id"], "equipamentos", "exemplo.escolhas.equipamento_id")

    effects = load("efeitos")
    if not isinstance(effects, list):
        fail("efeitos: deve ser uma lista")
    effect_ids = set()
    for effect in effects:
        effect_id = effect["id"]
        if effect_id in effect_ids or not effect["descricao"]:
            fail(f"efeito invalido ou repetido: {effect_id}")
        effect_ids.add(effect_id)
        duration = effect["duracao_turnos"]
        if duration is not None and (not isinstance(duration, int) or duration < 1):
            fail(f"{effect_id}: duracao invalida")
    item_table = load("tabela_itens")
    if not isinstance(item_table, dict) or not item_table:
        fail("tabela_itens: categorias ausentes")
    for category, items in item_table.items():
        if not isinstance(items, list) or not items:
            fail(f"tabela_itens/{category}: itens ausentes")
        for item in items:
            reference(item, "equipamentos", f"tabela_itens/{category}")

    return {name: len(records) for name, records in data.items()}


if __name__ == "__main__":
    try:
        counts = validate()
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        print(f"FALHA: {error}", file=sys.stderr)
        raise SystemExit(1)
    print("OK: validação concluída")
    for name in COLLECTIONS:
        print(f"{name}: {counts[name]}")
