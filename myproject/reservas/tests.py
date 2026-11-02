from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from biblioteca.models import Categoria, Livro, Membro
from reservas.models import Reserva


class ReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        """Cria dados usados somente no banco temporário dos testes."""
        cls.categoria = Categoria.objects.create(nome="Literatura")

        cls.livro = Livro.objects.create(
            titulo="Livro para testar reservas",
            categoria=cls.categoria,
            qtd_total=3,
            qtd_disponivel=3,
        )

        cls.outro_livro = Livro.objects.create(
            titulo="Outro livro",
            categoria=cls.categoria,
            qtd_total=2,
            qtd_disponivel=2,
        )

        cls.membros = [
            Membro.objects.create(
                nome_completo=f"Pessoa Teste {numero}",
                tipo_membro="ADMIN",
                email=f"pessoa{numero}@example.com",
            )
            for numero in range(1, 5)
        ]

    def criar_reserva(self, membro=None, livro=None, **campos):
        """Facilita criar reservas com diferentes situações."""
        return Reserva.objects.create(
            membro=membro or self.membros[0],
            livro=livro or self.livro,
            **campos,
        )

    def test_nova_reserva_entra_na_fila(self):
        reserva = self.criar_reserva()

        self.assertEqual(reserva.status, Reserva.Status.NA_FILA)
        self.assertIsNotNone(reserva.criada_em)

    def test_tokens_sao_diferentes(self):
        primeira = self.criar_reserva(membro=self.membros[0])
        segunda = self.criar_reserva(membro=self.membros[1])

        self.assertIsNotNone(primeira.token)
        self.assertNotEqual(primeira.token, segunda.token)

    def test_tres_reservas_ocupam_posicoes_consecutivas(self):
        reservas = [
            self.criar_reserva(membro=membro)
            for membro in self.membros[:3]
        ]

        self.assertEqual(
            [reserva.posicao_na_fila() for reserva in reservas],
            [1, 2, 3],
        )

    def test_reserva_de_outro_livro_nao_altera_posicao(self):
        self.criar_reserva(livro=self.outro_livro)
        reserva = self.criar_reserva()

        self.assertEqual(reserva.posicao_na_fila(), 1)

    def test_reserva_cancelada_nao_ocupa_posicao(self):
        primeira = self.criar_reserva(membro=self.membros[0])
        segunda = self.criar_reserva(membro=self.membros[1])

        primeira.status = Reserva.Status.CANCELADA
        primeira.save(update_fields=["status"])

        self.assertEqual(segunda.posicao_na_fila(), 1)

    def test_reserva_aguardando_retirada_nao_ocupa_fila(self):
        self.criar_reserva(
            membro=self.membros[0],
            status=Reserva.Status.AGUARDANDO_RETIRADA,
        )
        reserva = self.criar_reserva(membro=self.membros[1])

        self.assertEqual(reserva.posicao_na_fila(), 1)

    def test_empate_na_data_e_desempatado_pelo_id(self):
        primeira = self.criar_reserva(membro=self.membros[0])
        segunda = self.criar_reserva(membro=self.membros[1])

        # Simula duas reservas com exatamente a mesma data.
        instante = timezone.now()
        Reserva.objects.filter(
            pk__in=[primeira.pk, segunda.pk]
        ).update(criada_em=instante)

        primeira.refresh_from_db()
        segunda.refresh_from_db()

        self.assertEqual(primeira.posicao_na_fila(), 1)
        self.assertEqual(segunda.posicao_na_fila(), 2)

    def test_reserva_fora_da_fila_nao_tem_posicao(self):
        for status in (
            Reserva.Status.AGUARDANDO_RETIRADA,
            Reserva.Status.CONCLUIDA,
            Reserva.Status.EXPIRADA,
            Reserva.Status.CANCELADA,
        ):
            with self.subTest(status=status):
                reserva = self.criar_reserva(status=status)
                self.assertIsNone(reserva.posicao_na_fila())

    def test_reserva_nao_salva_nao_tem_posicao(self):
        reserva = Reserva(
            membro=self.membros[0],
            livro=self.livro,
        )

        self.assertIsNone(reserva.posicao_na_fila())

    def test_aguardando_retirada_com_prazo_passado_esta_vencida(self):
        reserva = self.criar_reserva(
            status=Reserva.Status.AGUARDANDO_RETIRADA,
            expira_em=timezone.now() - timedelta(minutes=1),
        )

        self.assertTrue(reserva.esta_vencida())

    def test_aguardando_retirada_com_prazo_futuro_nao_esta_vencida(self):
        reserva = self.criar_reserva(
            status=Reserva.Status.AGUARDANDO_RETIRADA,
            expira_em=timezone.now() + timedelta(hours=1),
        )

        self.assertFalse(reserva.esta_vencida())

    def test_reserva_sem_prazo_nao_esta_vencida(self):
        reserva = self.criar_reserva(
            status=Reserva.Status.AGUARDANDO_RETIRADA,
        )

        self.assertFalse(reserva.esta_vencida())

    def test_reserva_vence_no_instante_do_prazo(self):
        instante = timezone.now()
        reserva = self.criar_reserva(
            status=Reserva.Status.AGUARDANDO_RETIRADA,
            expira_em=instante,
        )

        with patch("reservas.models.timezone.now", return_value=instante):
            self.assertTrue(reserva.esta_vencida())

    def test_outros_status_nao_sao_considerados_vencidos(self):
        for status in (
            Reserva.Status.NA_FILA,
            Reserva.Status.CONCLUIDA,
            Reserva.Status.EXPIRADA,
            Reserva.Status.CANCELADA,
        ):
            with self.subTest(status=status):
                reserva = self.criar_reserva(
                    status=status,
                    expira_em=timezone.now() - timedelta(days=1),
                )
                self.assertFalse(reserva.esta_vencida())

    def test_consultar_vencimento_nao_altera_status(self):
        reserva = self.criar_reserva(
            status=Reserva.Status.AGUARDANDO_RETIRADA,
            expira_em=timezone.now() - timedelta(hours=1),
        )

        reserva.esta_vencida()
        reserva.refresh_from_db()

        self.assertEqual(
            reserva.status,
            Reserva.Status.AGUARDANDO_RETIRADA,
        )


class QuantidadeLivreParaReservaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.categoria = Categoria.objects.create(nome="Ciências")

        cls.livro = Livro.objects.create(
            titulo="Livro com três exemplares",
            categoria=cls.categoria,
            qtd_total=3,
            qtd_disponivel=3,
        )

        cls.outro_livro = Livro.objects.create(
            titulo="Livro independente",
            categoria=cls.categoria,
            qtd_total=2,
            qtd_disponivel=2,
        )

        cls.membros = [
            Membro.objects.create(
                nome_completo=f"Integrante Teste {numero}",
                tipo_membro="ADMIN",
                email=f"integrante{numero}@example.com",
            )
            for numero in range(1, 5)
        ]

    def criar_reserva(self, membro, status, livro=None):
        return Reserva.objects.create(
            membro=membro,
            livro=livro or self.livro,
            status=status,
        )

    def test_sem_reservas_todos_exemplares_estao_livres(self):
        self.assertEqual(self.livro.qtd_livre_para_reserva, 3)

    def test_uma_reserva_aguardando_segura_um_exemplar(self):
        self.criar_reserva(
            self.membros[0],
            Reserva.Status.AGUARDANDO_RETIRADA,
        )

        self.assertEqual(self.livro.qtd_livre_para_reserva, 2)

    def test_duas_reservas_aguardando_seguram_dois_exemplares(self):
        for membro in self.membros[:2]:
            self.criar_reserva(
                membro,
                Reserva.Status.AGUARDANDO_RETIRADA,
            )

        self.assertEqual(self.livro.qtd_livre_para_reserva, 1)

    def test_outros_status_nao_seguram_exemplares(self):
        for membro, status in zip(
            self.membros,
            (
                Reserva.Status.NA_FILA,
                Reserva.Status.CONCLUIDA,
                Reserva.Status.EXPIRADA,
                Reserva.Status.CANCELADA,
            ),
        ):
            self.criar_reserva(membro, status)

        self.assertEqual(self.livro.qtd_livre_para_reserva, 3)

    def test_reserva_de_outro_livro_nao_reduz_quantidade(self):
        self.criar_reserva(
            self.membros[0],
            Reserva.Status.AGUARDANDO_RETIRADA,
            livro=self.outro_livro,
        )

        self.assertEqual(self.livro.qtd_livre_para_reserva, 3)

    def test_quantidade_livre_nunca_fica_negativa(self):
        self.livro.qtd_disponivel = 1
        self.livro.save(update_fields=["qtd_disponivel"])

        for membro in self.membros[:2]:
            self.criar_reserva(
                membro,
                Reserva.Status.AGUARDANDO_RETIRADA,
            )

        self.assertEqual(self.livro.qtd_livre_para_reserva, 0)

    def test_consulta_nao_modifica_estoque_fisico(self):
        self.criar_reserva(
            self.membros[0],
            Reserva.Status.AGUARDANDO_RETIRADA,
        )

        self.assertEqual(self.livro.qtd_livre_para_reserva, 2)

        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, 3)
        self.assertTrue(self.livro.disponivel)