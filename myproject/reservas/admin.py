from django.contrib import admin

from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = (
        "membro",
        "livro",
        "status",
        "criada_em",
        "expira_em",
    )

    list_filter = (
        "status",
        "criada_em",
    )

    search_fields = (
        "membro__nome_completo",
        "membro__ra",
        "membro__siape",
        "livro__titulo",
    )

    readonly_fields = (
        "token",
        "criada_em",
    )

    list_select_related = (
        "membro",
        "livro",
    )

    fieldsets = (
        (
            "Reserva",
            {
                "fields": (
                    "membro",
                    "livro",
                    "status",
                ),
            },
        ),
        (
            "Datas",
            {
                "fields": (
                    "criada_em",
                    "notificada_em",
                    "expira_em",
                    "aceita_em",
                    "encerrada_em",
                ),
            },
        ),
        (
            "Identificação",
            {
                "fields": ("token",),
            },
        ),
    )