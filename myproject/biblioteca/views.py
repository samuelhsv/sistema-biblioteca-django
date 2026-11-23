from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views import View

from .models import Membro


def inicio(request):
    membro = None

    if request.user.is_authenticated:
        try:
            membro = request.user.membro
        except ObjectDoesNotExist:
            pass

    return render(
        request,
        "biblioteca/inicio.html",
        {"membro": membro},
    )

class MinhaContaView(LoginRequiredMixin, View):
    template_name = "biblioteca/minha_conta.html"

    def get(self, request):
        try:
            membro = request.user.membro
        except ObjectDoesNotExist:
            messages.warning(
                request,
                "Seu usuário não possui um cadastro de membro."
            )
            return redirect("inicio")

        emprestimos_ativos = membro.livros_emprestados.filter(
            status__in=["EMPRESTADO", "ATRASADO"]
        ).select_related("livro").order_by("data_prevista_devolucao")

        hoje = timezone.localdate()

        for emprestimo in emprestimos_ativos:
            diferenca = (
                emprestimo.data_prevista_devolucao - hoje
            ).days

            emprestimo.dias_restantes = max(diferenca, 0)
            emprestimo.dias_atraso = max(-diferenca, 0)
            emprestimo.vence_hoje = diferenca == 0


        reservas = membro.reservas.select_related(
            "livro"
        ).order_by("criada_em")

        historico = membro.livros_emprestados.filter(
            status="DEVOLVIDO"
        ).select_related("livro").order_by("-data_devolucao")

        paginador = Paginator(historico, 5)
        pagina = request.GET.get("pagina")
        historico_paginado = paginador.get_page(pagina)

        return render(
            request,
            self.template_name,
            {
                "membro": membro,
                "emprestimos_ativos": emprestimos_ativos,
                "reservas": reservas,
                "historico": historico_paginado,
            },
    )