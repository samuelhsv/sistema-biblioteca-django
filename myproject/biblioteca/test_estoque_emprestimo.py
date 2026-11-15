from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Categoria, Emprestimo, Livro, Membro


class EstoqueEmprestimoTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome="Literatura")
        self.livro = Livro.objects.create(
            titulo="Livro de teste",
            categoria=categoria,
            qtd_total=1,
            qtd_disponivel=1,
            disponivel=True,
        )
        self.membro = Membro.objects.create(
            nome_completo="Maria Santos",
            tipo_membro="ADMIN",
        )

    def test_recusa_novo_emprestimo_quando_estoque_esta_zerado(self):
        # Simula estoque inconsistente: a flag diz disponível, mas não há exemplares.
        Livro.objects.filter(pk=self.livro.pk).update(qtd_disponivel=0)

        with self.assertRaises(ValidationError) as erro:
            Emprestimo.objects.create(livro=self.livro, membro=self.membro)

        self.assertIn("livro", erro.exception.message_dict)
        self.assertFalse(Emprestimo.objects.filter(livro=self.livro).exists())
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, 0)

    def test_falha_ao_gravar_emprestimo_reverte_alteracao_de_estoque(self):
        def falhar_apos_baixa(*args, **kwargs):
            self.livro.refresh_from_db()
            self.assertEqual(self.livro.qtd_disponivel, 0)
            self.assertFalse(self.livro.disponivel)
            raise RuntimeError("Falha simulada na gravação do empréstimo")

        with patch.object(Emprestimo, "save_base", side_effect=falhar_apos_baixa):
            with self.assertRaisesMessage(RuntimeError, "Falha simulada"):
                Emprestimo.objects.create(livro=self.livro, membro=self.membro)

        self.assertFalse(Emprestimo.objects.filter(livro=self.livro).exists())
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, 1)
        self.assertTrue(self.livro.disponivel)
