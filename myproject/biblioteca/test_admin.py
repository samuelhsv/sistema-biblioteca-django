from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import Autor, Categoria, Emprestimo, Livro, Membro


class PainelAdministrativoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario = get_user_model().objects.create_superuser(
            username="admin_teste",
        )
        cls.categoria = Categoria.objects.create(nome="Categoria de teste")
        cls.autor = Autor.objects.create(primeiro_nome="Ana", sobrenome="Silva")
        cls.membro = Membro.objects.create(
            nome_completo="Pessoa de Teste",
            tipo_membro="ADMIN",
        )

    def setUp(self):
        self.client.force_login(self.usuario)

    def test_listas_do_admin_abrem(self):
        for modelo in ("livro", "emprestimo", "membro", "categoria", "autor"):
            with self.subTest(modelo=modelo):
                url = reverse(f"admin:biblioteca_{modelo}_changelist")
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_livro_novo_inicia_com_estoque_total_e_edicao_preserva_saldo(self):
        dados = {
            "titulo": "Livro de teste",
            "autores": [self.autor.pk],
            "categoria": self.categoria.pk,
            "qtd_total": 3,
            "disponivel": "on",
            "_save": "Salvar",
        }
        url = reverse("admin:biblioteca_livro_add")
        self.assertEqual(self.client.post(url, dados).status_code, 302)

        livro = Livro.objects.get(titulo="Livro de teste")
        self.assertEqual(livro.qtd_disponivel, 3)

        Emprestimo.objects.create(membro=self.membro, livro=livro)
        url = reverse("admin:biblioteca_livro_change", args=[livro.pk])
        dados.update(titulo="Título alterado", qtd_disponivel=99)

        self.assertEqual(self.client.post(url, dados).status_code, 302)
        livro.refresh_from_db()
        self.assertEqual(livro.titulo, "Título alterado")
        self.assertEqual(livro.qtd_disponivel, 2)

    def test_acao_devolve_emprestado_e_atrasado_sem_repor_duas_vezes(self):
        livro = Livro.objects.create(
            titulo="Livro emprestado",
            categoria=self.categoria,
            qtd_total=3,
            qtd_disponivel=3,
        )
        primeiro = Emprestimo.objects.create(membro=self.membro, livro=livro)
        segundo = Emprestimo.objects.create(membro=self.membro, livro=livro)
        segundo.status = "ATRASADO"
        segundo.save(update_fields=["status"])

        livro.refresh_from_db()
        self.assertEqual(livro.qtd_disponivel, 1)

        url = reverse("admin:biblioteca_emprestimo_changelist")
        dados = {
            "action": "marcar_como_devolvido",
            "_selected_action": [primeiro.pk, segundo.pk],
            "index": 0,
        }
        self.assertEqual(self.client.post(url, dados).status_code, 302)

        for emprestimo in (primeiro, segundo):
            emprestimo.refresh_from_db()
            self.assertEqual(emprestimo.status, "DEVOLVIDO")
            self.assertEqual(emprestimo.data_devolucao, timezone.localdate())

        livro.refresh_from_db()
        self.assertEqual(livro.qtd_disponivel, 3)

        # Aumenta o limite para que ele não esconda uma reposição indevida.
        livro.qtd_total = 5
        livro.save(update_fields=["qtd_total"])

        self.assertEqual(self.client.post(url, dados).status_code, 302)
        livro.refresh_from_db()
        self.assertEqual(livro.qtd_disponivel, 3)