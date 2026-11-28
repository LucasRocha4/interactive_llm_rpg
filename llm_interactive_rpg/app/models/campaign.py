from django.conf import settings
from django.db import models


class Campaign(models.Model):
    """Uma campanha de RPG (modo solo: um jogador, um macaco por vez)."""

    dono = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="campanhas",
    )
    nome = models.CharField(max_length=120)
    descricao = models.TextField(blank=True)
    # usado pelo ContextBuilder para filtrar lore e NPCs presentes
    local_atual = models.CharField(max_length=100, blank=True)
    ativa = models.BooleanField(default=True)
    criada_em = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome