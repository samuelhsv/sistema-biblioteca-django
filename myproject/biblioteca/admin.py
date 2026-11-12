from django.contrib import admin, messages
from django.db import transaction
from django.utils import timezone
from django.utils.html import format_html

from .models import Autor, Categoria, Curso, Emprestimo, Livro, Membro


admin.site.site_title = "Biblioteca FLUI"
admin.site.site_header = "Biblioteca FLUI · Administração"
admin.site.index_title = "Painel de Controle e Gestão"


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ("nome",)


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    list_display = ("primeiro_nome", "sobrenome")
    search_fields = ("primeiro_nome", "sobrenome")


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    ordering = ("nome",)


class EmprestimoInline(admin.TabularInline):
    model = Emprestimo
    fields = (
        "livro",
        "data_emprestimo",
        "data_prevista_devolucao",
        "data_devolucao",
        "status",
    )
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


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
    search_fields = ("nome_completo", "ra", "siape", "email")
    list_select_related = ("curso",)
    inlines = (EmprestimoInline,)

    fieldsets = (
        (
            "Dados pessoais",
            {"fields": ("nome_completo", "tipo_membro", "email", "telefone")},
        ),
        (
            "Vínculo acadêmico",
            {"fields": ("ra", "siape", "curso", "periodo")},
        ),
    )


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = (
        "membro",
        "livro",
        "data_emprestimo",
        "data_prevista_devolucao",
        "status_colorido",
        "dias_de_atraso",
    )
    list_filter = ("status", "membro__tipo_membro", "data_emprestimo")
    date_hierarchy = "data_emprestimo"
    search_fields = (
        "membro__nome_completo",
        "membro__ra",
        "membro__siape",
        "livro__titulo",
    )
    autocomplete_fields = ("membro", "livro")
    list_select_related = ("membro", "livro")
    actions = ("marcar_como_devolvido",)

    @admin.display(description="Status", ordering="status")
    def status_colorido(self, obj):
        cores = {
            "EMPRESTADO": "#1d4ed8",
            "ATRASADO": "#b91c1c",
            "DEVOLVIDO": "#15803d",
        }
        return format_html(
            '<strong style="color: {}">{}</strong>',
            cores.get(obj.status, "inherit"),
            obj.get_status_display(),
        )

    @admin.display(description="Dias de atraso")
    def dias_de_atraso(self, obj):
        if not obj.data_prevista_devolucao:
            return None

        if obj.status == "DEVOLVIDO":
            if not obj.data_devolucao:
                return None
            referencia = obj.data_devolucao
        else:
            referencia = timezone.localdate()

        return max((referencia - obj.data_prevista_devolucao).days, 0)

    @admin.action(description="Marcar como devolvido", permissions=["change"])
    def marcar_como_devolvido(self, request, queryset):
        ativos = {"EMPRESTADO", "ATRASADO"}
        data_devolucao = timezone.localdate()
        devolvidos = ignorados = 0

        for pk in queryset.values_list("pk", flat=True):
            with transaction.atomic():
                emprestimo = (
                    Emprestimo.objects.select_for_update().filter(pk=pk).first()
                )
                if (
                    emprestimo is None
                    or emprestimo.status not in ativos
                    or not self.has_change_permission(request, emprestimo)
                ):
                    ignorados += 1
                    continue

                emprestimo.livro = Livro.objects.select_for_update().get(
                    pk=emprestimo.livro_id
                )
                emprestimo.status = "DEVOLVIDO"
                emprestimo.data_devolucao = data_devolucao
                emprestimo.save(update_fields=["status", "data_devolucao"])
                devolvidos += 1

        if devolvidos:
            self.message_user(
                request,
                f"Devoluções registradas: {devolvidos}.",
                messages.SUCCESS,
            )

        if ignorados:
            self.message_user(
                request,
                f"Registros ignorados: {ignorados}.",
                messages.WARNING,
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
    readonly_fields = ("image_preview", "qtd_disponivel")
    list_display = (
        "titulo",
        "image_preview",
        "categoria",
        "qtd_total",
        "qtd_disponivel",
        "disponivel",
    )
    list_filter = ("categoria", "disponivel")
    search_fields = ("titulo", "autores__primeiro_nome", "autores__sobrenome")
    filter_horizontal = ("autores",)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.qtd_disponivel = obj.qtd_total
            if obj.qtd_disponivel == 0:
                obj.disponivel = False

        super().save_model(request, obj, form, change)

    @admin.display(description="Capa")
    def image_preview(self, obj):
        if obj and obj.capa:
            return format_html(
                '<img src="{}" style="width: 90px; height: auto;" />',
                obj.capa.url,
            )
        return "Sem imagem"