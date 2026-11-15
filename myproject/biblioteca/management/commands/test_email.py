from django.core.management.base import BaseCommand
from biblioteca.utils import enviar_email


class Command(BaseCommand):
    help = "Testa o envio de e-mail da Biblioteca FLUI"

    def handle(self, *args, **kwargs):
        enviar_email(
            assunto="Teste de e-mail - Biblioteca FLUI",
            template="emails/teste.txt",
            contexto={
                "nome": "Usuário de teste",
            },
            destinatario="seu-email@exemplo.com",
        )

        self.stdout.write(
            self.style.SUCCESS("Função enviar_email executada!")
        )