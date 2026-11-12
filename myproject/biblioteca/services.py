
from django.utils import timezone

from .models import Emprestimo


def marcar_atrasados():
    hoje = timezone.localdate()

    vencidos = Emprestimo.objects.filter(
        status="EMPRESTADO",
        data_prevista_devolucao__lt=hoje
    )

    total = 0

    for emp in vencidos:
        emp.status = "ATRASADO"
        emp.save()
        total += 1

    return total
