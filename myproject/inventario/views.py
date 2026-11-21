from django.shortcuts import render
from .models import Conferencia, ItemConferencia
from django.db import models

def relatorio_divergencias(request, conferencia_id):
    conferencia = Conferencia.objects.get(id=conferencia_id)

    itens = ItemConferencia.objects.filter(
        conferencia=conferencia,
        qtd_encontrada__isnull=False
    ).exclude(qtd_encontrada=models.F("qtd_esperada"))

    return render(request, "inventario/relatorio_divergencias.html", {
        "conferencia": conferencia,
        "itens": itens
    })