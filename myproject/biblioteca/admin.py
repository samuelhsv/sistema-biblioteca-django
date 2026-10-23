from django.contrib import admin
from django.utils.html import mark_safe

from .models import Autor, Categoria, Curso, Emprestimo, Livro, Membro


admin.site.site_title = "Biblioteca FLUI"
admin.site.site_header = "Biblioteca Comunitária FLUI"
admin.site.index_title = "Painel de Controle e Gestão"


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = (
        "nome_completo",
        "tipo_membro",
        "ra",
        "siape",
        "curso",
        "periodo",
        "email",
    )
    list_filter = ("tipo_membro", "curso")
    search_fields = (
        "nome_completo",
        "ra",
        "siape",
        "email",
    )
    list_select_related = ("curso",)

    fieldsets = (
        (
            "Dados pessoais",
            {
                "fields": (
                    "nome_completo",
                    "tipo_membro",
                    "email",
                    "telefone",
                )
            },
        ),
        (
            "Vínculo acadêmico",
            {
                "fields": (
                    "ra",
                    "siape",
                    "curso",
                    "periodo",
                )
            },
        ),
    )


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = (
        "livro",
        "membro",
        "data_emprestimo",
        "data_prevista_devolucao",
        "status",
    )
    list_filter = ("status", "data_emprestimo")
    search_fields = (
        "membro__nome_completo",
        "livro__titulo",
        "membro__ra",
    )


@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    fields = (
        "capa",
        "image_preview",
        "titulo",
        "autores",
        "categoria",
        "qtd_total",
        "qtd_disponivel",
        "disponivel",
    )
    readonly_fields = ("image_preview",)
    list_display = (
        "titulo",
        "image_preview",
        "categoria",
        "disponivel",
    )
    list_filter = ("disponivel", "categoria")
    search_fields = (
        "titulo",
        "autores__primeiro_nome",
        "autores__sobrenome",
    )

    @admin.display(description="Capa")
    def image_preview(self, obj):
        if obj.capa:
            return mark_safe(
                f'<img src="{obj.capa.url}" '
                'style="width: 90px; height: auto;" />'
            )
        return "Sem imagem"


admin.site.register(Categoria)
admin.site.register(Autor)