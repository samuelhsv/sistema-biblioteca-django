from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from dataclasses import dataclass
from typing import Optional

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

class Situacao:
    SEM_LOGIN = "SEM_LOGIN"
    NA_FILA = "NA_FILA"
    AGUARDANDO_RETIRADA = "AGUARDANDO_RETIRADA"
    PENDENCIA = "PENDENCIA"
    LIVRE = "LIVRE"
    SEM_EXEMPLAR = "SEM_EXEMPLAR"


@dataclass(frozen=True)
class SituacaoReserva:
    codigo: str
    reserva: Optional[Reserva] = None
    posicao: Optional[int] = None
    fila: int = 0


def situacao_reserva(membro, livro):
    """membro=None quer dizer: visitante ou usuário sem Membro vinculado."""
    fila = Reserva.objects.filter(livro=livro, status=Reserva.Status.NA_FILA).count()

    if membro is None:
        return SituacaoReserva(Situacao.SEM_LOGIN, fila=fila)

    reserva = Reserva.objects.filter(membro=membro, livro=livro, status__in=STATUS_ATIVOS).first()
    if reserva is not None:
        if reserva.status == Reserva.Status.AGUARDANDO_RETIRADA:
            return SituacaoReserva(Situacao.AGUARDANDO_RETIRADA, reserva=reserva, fila=fila)
        return SituacaoReserva(Situacao.NA_FILA, reserva=reserva,
                               posicao=reserva.posicao_na_fila(), fila=fila)

    if membro.possui_pendencia():
        return SituacaoReserva(Situacao.PENDENCIA, fila=fila)
    if livro.qtd_livre_para_reserva > 0:
        return SituacaoReserva(Situacao.LIVRE, fila=fila)
    return SituacaoReserva(Situacao.SEM_EXEMPLAR, fila=fila)