
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from biblioteca.models import Livro
from .models import Conferencia, ItemConferencia
from django.contrib import admin
from django.test import RequestFactory
from .admin import ItemConferenciaInline 


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

    def test_bloqueia_alteracoes_apos_finalizar(self):
        usuario = get_user_model().objects.create_superuser(
            username="admin2",
            email="admin2@email.com",
            password="senha123"
        )

        conferencia = Conferencia.objects.create(
            responsavel=usuario,
            finalizada=True
        )

        request = RequestFactory().get("/admin/")
        request.user = usuario

        inline = ItemConferenciaInline(Conferencia, admin.site)

        self.assertFalse(
            inline.has_change_permission(request, conferencia)
        )
        self.assertFalse(
            inline.has_add_permission(request, conferencia)
        )
        self.assertFalse(
            inline.has_delete_permission(request, conferencia)
        )

    def test_relatorio_apresenta_divergencias(self):
        usuario = get_user_model().objects.create_user(
            username="usuario_teste",
            password="senha123"
        )

        conferencia = Conferencia.objects.create(
            responsavel=usuario
        )

        livro = Livro.objects.create(
            titulo="Livro com divergencia",
            qtd_total=5,
            qtd_disponivel=3
        )

        item = ItemConferencia.objects.create(
            conferencia=conferencia,
            livro=livro,
            qtd_esperada=3,
            qtd_encontrada=1
        )

        url = reverse(
            "inventario:relatorio_divergencias",
            args=[conferencia.pk]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Livro com divergencia")
        self.assertContains(response, "-2")
        self.assertEqual(list(response.context["itens"]), [item])

    def test_relatorio_sem_divergencias(self):
        usuario = get_user_model().objects.create_user(
            username="usuario_sem_divergencia",
            password="senha123"
        )

        conferencia = Conferencia.objects.create(
            responsavel=usuario
        )

        livro = Livro.objects.create(
            titulo="Livro sem divergencia",
            qtd_total=5,
            qtd_disponivel=3
        )

        ItemConferencia.objects.create(
            conferencia=conferencia,
            livro=livro,
            qtd_esperada=3,
            qtd_encontrada=3
        )

        url = reverse(
            "inventario:relatorio_divergencias",
            args=[conferencia.pk]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["itens"]), 0)
        self.assertContains(
    response,
    "Não foram encontradas divergências nesta conferência."
)

    def test_relatorio_identifica_itens_nao_conferidos(self):
        usuario = get_user_model().objects.create_user(
            username="usuario_pendente",
            password="senha123"
        )

        conferencia = Conferencia.objects.create(
            responsavel=usuario
        )

        livro = Livro.objects.create(
            titulo="Livro pendente",
            qtd_total=5,
            qtd_disponivel=3
        )

        item = ItemConferencia.objects.create(
            conferencia=conferencia,
            livro=livro,
            qtd_esperada=3,
            qtd_encontrada=None
        )

        url = reverse(
            "inventario:relatorio_divergencias",
            args=[conferencia.pk]
        )

        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(list(response.context["itens"]), [])
        self.assertEqual(
            list(response.context["itens_nao_conferidos"]),
            [item]
        )
        self.assertContains(response, "Itens ainda não conferidos")
        self.assertContains(response, "Livro pendente")
        self.assertContains(response, "Aguardando conferência")

        
