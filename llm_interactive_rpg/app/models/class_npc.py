from django.db import models

from .campaign import Campaign


class NPC(models.Model):
    """Personagem controlado pelo narrador. As regras ainda não definem
    Defesa, corações nem ataques de NPC, então esses campos são opcionais."""

    campanha = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name="npcs",
    )

    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    local = models.CharField(max_length=100, blank=True)
    ativo = models.BooleanField(default=True)

    # preencher só quando as regras de NPC existirem
    coracoes = models.JSONField(null=True, blank=True)
    defesa = models.PositiveSmallIntegerField(null=True, blank=True)
    condicoes = models.JSONField(default=list, blank=True)

    # relação com o macaco (modo solo): número que sobe e desce;
    # escala não definida pelas regras; não armazenada como valor mecânico.

    def __str__(self):
        return self.nome
