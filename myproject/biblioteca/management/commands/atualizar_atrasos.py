
from django.core.management.base import BaseCommand

from biblioteca.services import marcar_atrasados


class Command(BaseCommand):
    help = "Atualiza os empréstimos que estão atrasados."

    def handle(self, *args, **options):
        total = marcar_atrasados()

        self.stdout.write(
            self.style.SUCCESS(
                f"{total} empréstimo(s) atualizado(s) para ATRASADO."
            )
        )
