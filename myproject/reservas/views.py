from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST

from biblioteca.models import Livro

from . import services
from .models import Reserva


def _membro_logado(request):
    return getattr(request.user, "membro", None)


def _destino(livro):
    # TODO(POR-04): trocar por livro.get_absolute_url() quando existir
    return "portal:inicio"


@login_required
@require_POST
def solicitar_reserva(request, livro_pk):
    livro = get_object_or_404(Livro, pk=livro_pk)
    membro = _membro_logado(request)
    if membro is None:
        messages.error(request, "Seu usuário não está vinculado a um membro da biblioteca.")
        return redirect(_destino(livro))
    try:
        reserva = services.solicitar(membro, livro)
    except ValidationError as erro:
        messages.error(request, " ".join(erro.messages))
    else:
        if reserva.status == Reserva.Status.AGUARDANDO_RETIRADA:
            prazo = timezone.localtime(reserva.expira_em)
            messages.success(request, f"Exemplar reservado! Retire até {prazo:%d/%m às %H:%M}.")
        else:
            messages.success(request, f"Você entrou na fila (posição {reserva.posicao_na_fila()}).")
    return redirect(_destino(livro))


@login_required
@require_POST
def cancelar_reserva(request, pk):
    reserva = get_object_or_404(Reserva, pk=pk, membro=_membro_logado(request))
    try:
        services.cancelar(reserva)
    except ValidationError as erro:
        messages.error(request, " ".join(erro.messages))
    else:
        messages.success(request, "Reserva cancelada.")
    return redirect(_destino(reserva.livro))