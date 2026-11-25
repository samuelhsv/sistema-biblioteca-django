from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View

from .models import Emprestimo


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
class RenovarEmprestimoView(LoginRequiredMixin, View):

    def post(self, request, pk):
        try:
            membro = request.user.membro
        except ObjectDoesNotExist:
            messages.error(request, "Você não possui cadastro de membro.")
            return redirect("inicio")

        emprestimo = get_object_or_404(
            Emprestimo,
            pk=pk,
            membro=membro,
        )

        try:
            emprestimo.renovar()
            messages.success(request, "Empréstimo renovado com sucesso!")
        except ValidationError as erro:
            messages.error(request, erro.message)

        return redirect("inicio")