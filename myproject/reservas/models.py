import uuid

from django.db import models
from django.db.models import Q
from django.utils import timezone


class Reserva(models.Model):
    class Status(models.TextChoices):
        NA_FILA = "NA_FILA", "Na fila"
        AGUARDANDO_RETIRADA = "AGUARDANDO", "Aguardando retirada"
        CONCLUIDA = "CONCLUIDA", "Concluída (retirada)"
        EXPIRADA = "EXPIRADA", "Expirada"
        CANCELADA = "CANCELADA", "Cancelada"

    membro = models.ForeignKey(
        "biblioteca.Membro",
        on_delete=models.CASCADE,
        related_name="reservas",
    )

    livro = models.ForeignKey(
        "biblioteca.Livro",
        on_delete=models.CASCADE,
        related_name="reservas",
    )

    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.NA_FILA,
    )

    criada_em = models.DateTimeField(
        auto_now_add=True,
        verbose_name="criada em",
    )

    notificada_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="notificada em",
    )

    expira_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="expira em",
    )

    aceita_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="aceita em",
    )

    encerrada_em = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="encerrada em",
    )

    token = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False,
    )

    class Meta:
        ordering = ["criada_em", "pk"]
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"
        indexes = [
            models.Index(
                fields=["livro", "status", "criada_em"],
                name="reserva_livro_status_data_idx",
            ),
        ]

    def posicao_na_fila(self):
        """
        Retorna a posição entre as reservas NA_FILA do mesmo livro.

        Reservas de outros livros e de outros status não entram
        na contagem. Em caso de datas iguais, o ID desempata.

        Retorna None se a reserva não foi salva ou não está na fila.
        """
        if self.pk is None or self.status != self.Status.NA_FILA:
            return None

        anteriores = (
            type(self)
            .objects.filter(
                livro_id=self.livro_id,
                status=self.Status.NA_FILA,
            )
            .filter(
                Q(criada_em__lt=self.criada_em)
                | Q(
                    criada_em=self.criada_em,
                    pk__lt=self.pk,
                )
            )
        )

        return anteriores.count() + 1

    def esta_vencida(self):
        """
        Indica se o prazo de retirada já foi atingido.

        Apenas reservas aguardando retirada podem estar vencidas.
        Este método consulta o prazo, mas não altera o status.
        A expiração automática pertence à tarefa RES-05.
        """
        return (
            self.status == self.Status.AGUARDANDO_RETIRADA
            and self.expira_em is not None
            and self.expira_em <= timezone.now()
        )

    def __str__(self):
        return (
            f"{self.livro} — {self.membro} "
            f"({self.get_status_display()})"
        )