from django.contrib import admin

from .models import Campaign, Character, Item, NPC


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("nome", "dono", "local_atual", "ativa", "criada_em")
    list_filter = ("ativa",)
    search_fields = ("nome", "descricao")
    readonly_fields = ("criada_em",)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("nome", "campanha", "nivel", "oficio_id", "pelagem_id", "defesa")
    list_filter = ("campanha", "nivel", "oficio_id", "pelagem_id")
    search_fields = ("nome", "campanha__nome")


@admin.register(NPC)
class NPCAdmin(admin.ModelAdmin):
    list_display = ("nome", "campanha", "local", "ativo")
    list_filter = ("campanha", "ativo")
    search_fields = ("nome", "campanha__nome", "descricao")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("id", "nome", "categoria", "dano", "protecao", "arremessavel")
    list_filter = ("categoria", "a_distancia", "arremessavel")
    search_fields = ("id", "nome")
