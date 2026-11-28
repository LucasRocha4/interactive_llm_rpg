import json
from pathlib import Path

from django.db import migrations


def popular_itens(apps, schema_editor):
    Item = apps.get_model("app", "Item")
    regras_root = Path(__file__).resolve().parents[1] / "regras"
    with (regras_root / "equipamentos.json").open(encoding="utf-8") as arquivo:
        itens = json.load(arquivo)

    campos = (
        "nome",
        "categoria",
        "dano",
        "protecao",
        "a_distancia",
        "arremessavel",
        "area_m",
        "recarga_turnos",
        "observacoes",
        "texto_original",
    )
    for item in itens:
        defaults = {campo: item.get(campo) for campo in campos}
        if defaults["observacoes"] is None:
            defaults["observacoes"] = ""
        Item.objects.update_or_create(
            pk=item["id"],
            defaults=defaults,
        )


class Migration(migrations.Migration):
    dependencies = [("app", "0001_initial")]

    operations = [migrations.RunPython(popular_itens, migrations.RunPython.noop)]
