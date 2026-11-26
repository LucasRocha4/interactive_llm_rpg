import json
from pathlib import Path

from django.contrib.auth import get_user_model
from django.db.models.signals import post_migrate
from django.dispatch import receiver


NOME_CAMPANHA_PADRAO = "Campanha padrão — ficha bongo_chule"
REGRAS_ROOT = Path(__file__).resolve().parent / "regras"


def _ler_json(nome):
    with (REGRAS_ROOT / f"{nome}.json").open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


@receiver(post_migrate, dispatch_uid="app.garantir_campanha_padrao_bongo")
def garantir_campanha_padrao(sender, using, **kwargs):
    if sender.label != "app":
        return

    from .models import Campaign, Character

    User = get_user_model()
    dono, _ = User.objects.using(using).get_or_create(
        username="campanha_demo_sistema",
        defaults={
            "password": "!",
            "is_superuser": False,
            "is_staff": False,
            "is_active": True,
        },
    )
    campanha, _ = Campaign.objects.using(using).get_or_create(
        nome=NOME_CAMPANHA_PADRAO,
        defaults={
            "dono": dono,
            "descricao": "Campanha padrão para testar a ficha oficial bongo_chule.",
            "local_atual": "Clareira",
            "ativa": True,
        },
    )

    if Character.objects.using(using).filter(campanha=campanha).exists():
        return

    fichas = _ler_json("exemplos_de_ficha")
    ficha = next((registro for registro in fichas if registro["id"] == "bongo_chule"), None)
    if ficha is None:
        raise RuntimeError("A ficha de exemplo 'bongo_chule' não existe.")

    regras_gerais = {regra["id"]: regra for regra in _ler_json("regras_gerais")}
    escolhas = ficha["escolhas"]
    oficio_id = escolhas["oficio_id"]
    nivel = escolhas["nivel"]
    tecnicas = [
        tecnica["id"]
        for tecnica in _ler_json("tecnicas")
        if tecnica["oficio_id"] == oficio_id and tecnica["nivel"] <= nivel
    ]
    coracoes = regras_gerais["coracoes"]["valores"]["iniciais"]
    infeccao = regras_gerais["infeccao"]["valores"]

    Character.objects.using(using).create(
        campanha=campanha,
        nome=ficha["nome"],
        nivel=nivel,
        pelagem_id=escolhas["pelagem_id"],
        oficio_id=oficio_id,
        defeito_id=escolhas["defeito_id"],
        atributos=ficha["atributos_calculados"],
        coracoes={"atual": coracoes, "maximo": coracoes},
        infeccao={"atual": infeccao["minimo"], "maximo": infeccao["maximo"]},
        equipamentos=[escolhas["equipamento_id"]],
        inventario={},
        tecnicas_disponiveis=tecnicas,
    )
