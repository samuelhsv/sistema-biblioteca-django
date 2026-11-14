from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import render


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