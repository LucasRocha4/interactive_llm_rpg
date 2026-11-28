import json
from functools import lru_cache
from pathlib import Path

from django.core.exceptions import ValidationError


REGRAS_ROOT = Path(__file__).resolve().parents[1] / "regras"


@lru_cache(maxsize=None)
def carregar_catalogo(nome: str):
    caminho = REGRAS_ROOT / f"{nome}.json"
    with caminho.open(encoding="utf-8") as arquivo:
        return json.load(arquivo)


def registros_por_id(nome: str) -> dict[str, dict]:
    return {str(registro["id"]): registro for registro in carregar_catalogo(nome)}


def validar_id(valor: str, catalogo: str, campo: str) -> dict:
    registro = registros_por_id(catalogo).get(valor)
    if registro is None:
        raise ValidationError({campo: f"ID '{valor}' não existe em {catalogo}.json."})
    return registro
