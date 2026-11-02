from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from simple_history.admin import SimpleHistoryAdmin

from biblioteca.models import Emprestimo, Livro

from .models import Reserva


@admin.register(Reserva)
class ReservaAdmin(SimpleHistoryAdmin):
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

    actions = ("registrar_retirada",)

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

    @admin.action(
        description="Registrar retirada (criar empréstimo)",
        permissions=["change"],
    )
    def registrar_retirada(self, request, queryset):
        """Conclui cada reserva e cria seu empréstimo na mesma transação."""
        permissao = (
            f"{Emprestimo._meta.app_label}."
            f"add_{Emprestimo._meta.model_name}"
        )

        if not request.user.has_perm(permissao):
            self.message_user(
                request,
                "Você não tem permissão para criar empréstimos.",
                level=messages.ERROR,
            )
            return

        concluidas = 0
        ignoradas = 0

        for identificador in queryset.values_list("pk", flat=True):
            try:
                with transaction.atomic():
                    # Reconsulta o registro para verificar o estado atual.
                    reserva = (
                        Reserva.objects.select_for_update()
                        .get(pk=identificador)
                    )

                    if reserva.status != Reserva.Status.AGUARDANDO_RETIRADA:
                        ignoradas += 1
                        continue

                    if reserva.esta_vencida():
                        raise ValidationError(
                            "O prazo de retirada desta reserva venceu."
                        )

                    # Usa o estoque atual do banco, sem reutilizar
                    # objetos relacionados carregados anteriormente.
                    livro = (
                        Livro.objects.select_for_update()
                        .get(pk=reserva.livro_id)
                    )

                    # Libera o exemplar reservado para esta retirada.
                    # Se ocorrer erro, a transação desfaz a conclusão.
                    reserva.status = Reserva.Status.CONCLUIDA
                    reserva.encerrada_em = timezone.now()
                    reserva._history_user = request.user
                    reserva.save(
                        update_fields=["status", "encerrada_em"]
                    )

                    emprestimo = Emprestimo(
                        membro=reserva.membro,
                        livro=livro,
                    )
                    emprestimo._history_user = request.user

                    # Valida antes de gravar.
                    # O save() existente faz o desconto do estoque.
                    emprestimo.full_clean()
                    emprestimo.save()

                concluidas += 1

            except ValidationError as erro:
                detalhes = "; ".join(erro.messages)
                self.message_user(
                    request,
                    f"Reserva #{identificador}: {detalhes}",
                    level=messages.ERROR,
                )

        if concluidas:
            self.message_user(
                request,
                f"Retiradas registradas: {concluidas}.",
                level=messages.SUCCESS,
            )

        if ignoradas:
            self.message_user(
                request,
                (
                    f"Reservas ignoradas: {ignoradas}. "
                    "A ação aceita somente reservas aguardando retirada."
                ),
                level=messages.WARNING,
            )