
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from biblioteca.models import Livro
from .models import Conferencia, ItemConferencia


class ItemConferenciaTests(TestCase):
    def test_calcula_diferenca(self):
        item = ItemConferencia(
            qtd_esperada=5,
            qtd_encontrada=3,
        )
        self.assertEqual(item.diferenca, -2)

    def test_gera_itens_com_quantidade_esperada(self):
        usuario = get_user_model().objects.create_superuser(
            username="admin",
            email="admin@email.com",
            password="senha123"
        )
        self.client.force_login(usuario)

        conferencia = Conferencia.objects.create(
            responsavel=usuario
        )

        livro = Livro.objects.create(
            titulo="Livro de teste",
            qtd_total=5,
            qtd_disponivel=3
        )

        url = reverse("admin:inventario_conferencia_changelist")

        self.client.post(url, {
            "action": "gerar_itens_acervo",
            "_selected_action": [conferencia.pk],
            "index": 0,
        })

        item = ItemConferencia.objects.get(
            conferencia=conferencia,
            livro=livro
        )

        self.assertEqual(item.qtd_esperada, 3)
