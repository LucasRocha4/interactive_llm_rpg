from django.contrib import admin

from models import Campaign, Character, Item, NPC


@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    list_display = ("nome", "dono", "local_atual", "ativa", "criada_em")
    list_filter = ("ativa",)
    search_fields = ("nome",)


@admin.register(Character)
class CharacterAdmin(admin.ModelAdmin):
    list_display = ("nome", "campanha", "nivel", "oficio_id", "pelagem_id", "defesa")
    list_filter = ("campanha", "oficio_id")
    search_fields = ("nome",)


@admin.register(NPC)
class NPCAdmin(admin.ModelAdmin):
    list_display = ("nome", "campanha", "local", "ativo")
    list_filter = ("campanha", "ativo")
    search_fields = ("nome",)


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ("nome", "categoria", "dano", "protecao", "a_distancia", "arremessavel")
    list_filter = ("categoria", "a_distancia")
    search_fields = ("id", "nome")