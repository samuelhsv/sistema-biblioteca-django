from datetime import timedelta
from unittest.mock import patch

from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.exceptions import ValidationError
from django.test import RequestFactory, TestCase
from django.utils import timezone

from biblioteca.models import Categoria, Emprestimo, Livro, Membro
from reservas.models import Reserva


class RegistrarRetiradaTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_user(
            username="bibliotecaria",
            is_staff=True,
            is_superuser=True,
        )

        self.categoria = Categoria.objects.create(nome="Literatura")

        self.livro = Livro.objects.create(
            titulo="Livro reservado",
            categoria=self.categoria,
            qtd_total=2,
            qtd_disponivel=2,
        )

        self.membro = Membro.objects.create(
            nome_completo="Pessoa de Teste",
            tipo_membro="ADMIN",
            email="pessoa@example.com",
        )

        self.reserva = Reserva.objects.create(
            membro=self.membro,
            livro=self.livro,
            status=Reserva.Status.AGUARDANDO_RETIRADA,
            expira_em=timezone.now() + timedelta(hours=24),
        )

        self.admin_reserva = admin.site._registry[Reserva]

    def executar_acao(self, reservas=None, usuario=None):
        """Executa a mesma ação usada pela listagem do admin."""
        request = RequestFactory().post("/admin/reservas/reserva/")
        request.user = usuario or self.usuario
        request.session = {}
        request._messages = FallbackStorage(request)

        if reservas is None:
            reservas = Reserva.objects.filter(pk=self.reserva.pk)

        self.admin_reserva.registrar_retirada(request, reservas)

        return list(get_messages(request))

    def test_retirada_cria_emprestimo_e_conclui_reserva(self):
        avisos = self.executar_acao()

        self.reserva.refresh_from_db()
        self.livro.refresh_from_db()

        emprestimo = Emprestimo.objects.get()

        self.assertEqual(emprestimo.membro_id, self.membro.pk)
        self.assertEqual(emprestimo.livro_id, self.livro.pk)
        self.assertEqual(emprestimo.status, "EMPRESTADO")
        self.assertEqual(
            self.reserva.status,
            Reserva.Status.CONCLUIDA,
        )
        self.assertIsNotNone(self.reserva.encerrada_em)
        self.assertEqual(self.livro.qtd_disponivel, 1)
        self.assertTrue(
            any(aviso.level == messages.SUCCESS for aviso in avisos)
        )

    def test_repetir_acao_nao_cria_outro_emprestimo(self):
        self.executar_acao()
        self.executar_acao()

        self.livro.refresh_from_db()

        self.assertEqual(Emprestimo.objects.count(), 1)
        self.assertEqual(self.livro.qtd_disponivel, 1)

    def test_outros_status_sao_ignorados(self):
        for status in (
            Reserva.Status.NA_FILA,
            Reserva.Status.CONCLUIDA,
            Reserva.Status.CANCELADA,
            Reserva.Status.EXPIRADA,
        ):
            with self.subTest(status=status):
                self.reserva.status = status
                self.reserva.save()

                avisos = self.executar_acao()

                self.reserva.refresh_from_db()
                self.livro.refresh_from_db()

                self.assertEqual(self.reserva.status, status)
                self.assertEqual(Emprestimo.objects.count(), 0)
                self.assertEqual(self.livro.qtd_disponivel, 2)
                self.assertTrue(
                    any(
                        aviso.level == messages.WARNING
                        for aviso in avisos
                    )
                )

    def test_reserva_vencida_nao_pode_ser_retirada(self):
        self.reserva.expira_em = (
            timezone.now() - timedelta(minutes=1)
        )
        self.reserva.save()

        avisos = self.executar_acao()

        self.reserva.refresh_from_db()
        self.livro.refresh_from_db()

        self.assertEqual(
            self.reserva.status,
            Reserva.Status.AGUARDANDO_RETIRADA,
        )
        self.assertIsNone(self.reserva.encerrada_em)
        self.assertEqual(Emprestimo.objects.count(), 0)
        self.assertEqual(self.livro.qtd_disponivel, 2)
        self.assertTrue(
            any(aviso.level == messages.ERROR for aviso in avisos)
        )

    def test_falha_na_validacao_desfaz_conclusao_e_historico(self):
        quantidade_historico = self.reserva.history.count()

        with patch.object(
            Emprestimo,
            "full_clean",
            side_effect=ValidationError("Falha de teste."),
        ):
            avisos = self.executar_acao()

        self.reserva.refresh_from_db()
        self.livro.refresh_from_db()

        self.assertEqual(
            self.reserva.status,
            Reserva.Status.AGUARDANDO_RETIRADA,
        )
        self.assertIsNone(self.reserva.encerrada_em)
        self.assertEqual(Emprestimo.objects.count(), 0)
        self.assertEqual(self.livro.qtd_disponivel, 2)
        self.assertEqual(
            self.reserva.history.count(),
            quantidade_historico,
        )
        self.assertTrue(
            any(aviso.level == messages.ERROR for aviso in avisos)
        )

    def test_membro_com_pendencia_impede_retirada(self):
        outro_livro = Livro.objects.create(
            titulo="Livro em atraso",
            categoria=self.categoria,
            qtd_total=1,
            qtd_disponivel=1,
        )

        Emprestimo.objects.create(
            membro=self.membro,
            livro=outro_livro,
            data_prevista_devolucao=(
                timezone.localdate() - timedelta(days=1)
            ),
        )

        self.executar_acao()

        self.reserva.refresh_from_db()
        self.livro.refresh_from_db()

        self.assertEqual(Emprestimo.objects.count(), 1)
        self.assertEqual(
            self.reserva.status,
            Reserva.Status.AGUARDANDO_RETIRADA,
        )
        self.assertIsNone(self.reserva.encerrada_em)
        self.assertEqual(self.livro.qtd_disponivel, 2)

    def test_ultimo_exemplar_reservado_pode_ser_retirado(self):
        self.livro.qtd_total = 1
        self.livro.qtd_disponivel = 1
        self.livro.save()

        self.assertEqual(self.livro.qtd_livre_para_reserva, 0)

        self.executar_acao()

        self.livro.refresh_from_db()
        self.reserva.refresh_from_db()

        self.assertEqual(Emprestimo.objects.count(), 1)
        self.assertEqual(self.livro.qtd_disponivel, 0)
        self.assertFalse(self.livro.disponivel)
        self.assertEqual(
            self.reserva.status,
            Reserva.Status.CONCLUIDA,
        )

    def test_duas_retiradas_descontam_um_exemplar_cada(self):
        outro_membro = Membro.objects.create(
            nome_completo="Outra Pessoa",
            tipo_membro="ADMIN",
            email="outra@example.com",
        )

        segunda = Reserva.objects.create(
            membro=outro_membro,
            livro=self.livro,
            status=Reserva.Status.AGUARDANDO_RETIRADA,
        )

        self.executar_acao(
            reservas=Reserva.objects.filter(
                pk__in=[self.reserva.pk, segunda.pk]
            )
        )

        self.livro.refresh_from_db()

        self.assertEqual(Emprestimo.objects.count(), 2)
        self.assertEqual(self.livro.qtd_disponivel, 0)
        self.assertFalse(self.livro.disponivel)
        self.assertEqual(
            Reserva.objects.filter(
                status=Reserva.Status.CONCLUIDA
            ).count(),
            2,
        )

    def test_usuario_sem_permissao_nao_cria_emprestimo(self):
        usuario = get_user_model().objects.create_user(
            username="sem_permissao",
            is_staff=True,
        )

        avisos = self.executar_acao(usuario=usuario)

        self.reserva.refresh_from_db()

        self.assertEqual(Emprestimo.objects.count(), 0)
        self.assertEqual(
            self.reserva.status,
            Reserva.Status.AGUARDANDO_RETIRADA,
        )
        self.assertTrue(
            any(aviso.level == messages.ERROR for aviso in avisos)
        )

    def test_retirada_registra_responsavel_no_historico(self):
        self.executar_acao()

        emprestimo = Emprestimo.objects.get()

        self.assertEqual(
            self.reserva.history.latest().history_user_id,
            self.usuario.pk,
        )
        self.assertEqual(
            emprestimo.history.latest().history_user_id,
            self.usuario.pk,
        )

    def test_balcao_recusa_quando_todos_exemplares_estao_reservados(self):
        self.livro.qtd_disponivel = 1
        self.livro.save()

        emprestimo = Emprestimo(
            membro=self.membro,
            livro=self.livro,
        )

        with self.assertRaises(ValidationError) as contexto:
            emprestimo.full_clean()

        self.assertIn("livro", contexto.exception.message_dict)
        self.assertIn(
            "Todos os exemplares disponíveis estão reservados",
            " ".join(contexto.exception.messages),
        )
        self.assertEqual(Emprestimo.objects.count(), 0)

    def test_balcao_permite_exemplar_nao_reservado(self):
        emprestimo = Emprestimo(
            membro=self.membro,
            livro=self.livro,
        )

        emprestimo.full_clean()
        emprestimo.save()

        self.livro.refresh_from_db()

        self.assertEqual(self.livro.qtd_disponivel, 1)
        self.assertEqual(self.livro.qtd_livre_para_reserva, 0)

    def test_membro_marcado_com_atraso_nao_pode_emprestar(self):
        outro_livro = Livro.objects.create(
            titulo="Outro livro em atraso",
            categoria=self.categoria,
            qtd_total=1,
            qtd_disponivel=1,
        )

        Emprestimo.objects.create(
            membro=self.membro,
            livro=outro_livro,
            status="ATRASADO",
        )

        emprestimo = Emprestimo(
            membro=self.membro,
            livro=self.livro,
        )

        with self.assertRaises(ValidationError) as contexto:
            emprestimo.full_clean()

        self.assertIn("membro", contexto.exception.message_dict)