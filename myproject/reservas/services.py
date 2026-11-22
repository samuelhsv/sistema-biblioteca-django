from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from .models import Reserva

PRAZO_RETIRADA = timedelta(hours=24)
LIMITE_RESERVAS_ATIVAS = 3
STATUS_ATIVOS = (Reserva.Status.NA_FILA, Reserva.Status.AGUARDANDO_RETIRADA)


def validar_solicitacao(membro, livro):
    """
    Levanta ValidationError com o motivo se o membro NÃO pode reservar o livro.
    """
    if membro.possui_pendencia():
        raise ValidationError("Você tem devolução pendente e não pode reservar novos livros.")

    ativas = Reserva.objects.filter(membro=membro, status__in=STATUS_ATIVOS)

    if ativas.filter(livro=livro).exists():
        raise ValidationError("Você já tem uma reserva ativa deste livro.")

    if membro.livros_emprestados.filter(
        livro=livro, status__in=["EMPRESTADO", "ATRASADO"]
    ).exists():
        raise ValidationError("Você já está com este livro emprestado.")

    if ativas.count() >= LIMITE_RESERVAS_ATIVAS:
        raise ValidationError(
            f"Você atingiu o limite de {LIMITE_RESERVAS_ATIVAS} reservas ativas."
        )


def liberar_para_retirada(reserva):
    """
    Marca a reserva como aguardando retirada. NÃO salva: quem chama salva.
    """
    agora = timezone.now()
    reserva.status = Reserva.Status.AGUARDANDO_RETIRADA
    reserva.notificada_em = agora
    reserva.expira_em = agora + PRAZO_RETIRADA
    # TODO(RES-04): enviar o e-mail de aviso aqui


@transaction.atomic
def solicitar(membro, livro):
    validar_solicitacao(membro, livro)
    reserva = Reserva(membro=membro, livro=livro)
    if livro.qtd_livre_para_reserva > 0:
        liberar_para_retirada(reserva)
    reserva.save()
    return reserva


@transaction.atomic
def cancelar(reserva):
    if reserva.status not in STATUS_ATIVOS:
        raise ValidationError("Esta reserva não pode mais ser cancelada.")
    estava_aguardando = reserva.status == Reserva.Status.AGUARDANDO_RETIRADA
    reserva.status = Reserva.Status.CANCELADA
    reserva.encerrada_em = timezone.now()
    reserva.save()
    if estava_aguardando:
        pass  # TODO(RES-03): promover_fila(reserva.livro)