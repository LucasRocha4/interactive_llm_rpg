from django.core.exceptions import ValidationError
from django.db import models

from .catalogos import registros_por_id


class Item(models.Model):
    """Catálogo de equipamentos. Espelha app/regras/equipamentos.json,
    com os mesmos nomes de campo, para poder carregar o JSON direto.
    O personagem guarda só o id do item (ex.: "machado_de_pedra")."""

    class Categoria(models.TextChoices):
        ARMA = "arma", "Arma"
        PROTECAO = "protecao", "Proteção"
        MUNICAO = "municao", "Munição"
        CONSUMIVEL = "consumivel", "Consumível"
        PONTOS_DE_MAGIA = "pontos_de_magia", "Pontos de magia"
        MATERIAL = "material", "Material"

    # id em texto, igual ao do JSON (ex.: "faca_de_pedra")
    id = models.CharField(primary_key=True, max_length=60)
    nome = models.CharField(max_length=100)
    categoria = models.CharField(max_length=30, choices=Categoria.choices)

    # dano e proteção são fixos; null quando o item não tem (ou as regras não definem)
    dano = models.PositiveSmallIntegerField(null=True, blank=True)
    protecao = models.PositiveSmallIntegerField(null=True, blank=True)

    # armas: True se ataca à distância (usa Pulo); null para itens que não são armas
    a_distancia = models.BooleanField(null=True, blank=True)
    arremessavel = models.BooleanField(default=False)
    area_m = models.FloatField(null=True, blank=True)
    recarga_turnos = models.PositiveSmallIntegerField(null=True, blank=True)

    observacoes = models.TextField(blank=True)
    texto_original = models.TextField(blank=True)

    def __str__(self):
        return self.nome

    def clean(self):
        super().clean()
        regra = registros_por_id("equipamentos").get(self.pk)
        if regra is None:
            raise ValidationError({"id": f"ID '{self.pk}' não existe em equipamentos.json."})

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
        divergencias = {
            campo: "Este valor deve corresponder ao catálogo de regras."
            for campo in campos
            if getattr(self, campo)
            != ("" if campo == "observacoes" and regra.get(campo) is None else regra.get(campo))
        }
        if divergencias:
            raise ValidationError(divergencias)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)
