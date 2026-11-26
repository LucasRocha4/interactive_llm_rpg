from __future__ import annotations

from typing import Any

from .parser_ia import criar_cena_atual, interpretar_acao
from .schemas import IntentJogador


def montar_contexto_do_banco(campanha: Any, ficha: Any, personagem: dict[str, Any] | None = None) -> dict[str, Any]:
    estado_personagem = personagem or ficha.para_estado_motor()
    cena = criar_cena_atual(estado_personagem)
    cena["personagem"] = estado_personagem
    cena["campanha"] = {
        "id": campanha.pk,
        "nome": campanha.nome,
        "descricao": campanha.descricao,
        "local_atual": campanha.local_atual,
    }
    cena["npcs"] = [
        {
            "id": f"npc_{npc.pk}",
            "nome": npc.nome,
            "tipo": "npc",
            "descricao": npc.descricao,
            "local": npc.local,
            "condicoes": list(npc.condicoes or []),
            **({"coracoes": npc.coracoes} if npc.coracoes else {}),
            **({"defesa": npc.defesa} if npc.defesa is not None else {}),
        }
        for npc in campanha.npcs.filter(ativo=True).order_by("pk")
    ]
    if campanha.local_atual:
        cena["locais"] = [{"id": campanha.local_atual, "nome": campanha.local_atual}]

    from app.models import Item

    itens = list(Item.objects.order_by("id"))
    cena["equipamentos_validos"] = [item.pk for item in itens]
    cena["catalogo_equipamentos"] = [
        {
            "id": item.pk,
            "nome": item.nome,
            "categoria": item.categoria,
            "dano": item.dano,
            "protecao": item.protecao,
            "a_distancia": item.a_distancia,
            "arremessavel": item.arremessavel,
            "area_m": item.area_m,
            "recarga_turnos": item.recarga_turnos,
        }
        for item in itens
    ]
    return cena


def interpretar_acao_da_campanha(
    texto: str,
    campanha: Any,
    ficha: Any,
    personagem: dict[str, Any],
    cena_atual: dict[str, Any],
) -> IntentJogador:
    contexto = montar_contexto_do_banco(campanha, ficha, personagem)
    contexto.update(cena_atual)
    return interpretar_acao(texto, personagem, contexto)


def persistir_npcs_da_cena(campanha: Any, cena: dict[str, Any]) -> None:
    from app.models import NPC

    for dados in cena.get("npcs", []):
        identificador = str(dados.get("id", ""))
        if not identificador.startswith("npc_"):
            continue
        try:
            npc_id = int(identificador.removeprefix("npc_"))
        except ValueError:
            continue
        npc = NPC.objects.filter(pk=npc_id, campanha=campanha).first()
        if npc is None:
            continue
        campos = []
        for campo in ("coracoes", "defesa", "condicoes"):
            if campo in dados:
                setattr(npc, campo, dados[campo])
                campos.append(campo)
        if campos:
            npc.save(update_fields=campos)
