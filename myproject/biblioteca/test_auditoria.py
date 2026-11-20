from django.contrib import admin
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from simple_history.admin import SimpleHistoryAdmin

from biblioteca.models import Categoria, Curso, Emprestimo, Livro, Membro
from reservas.models import Reserva


class AuditoriaTests(TestCase):
    def setUp(self):
        self.usuario = get_user_model().objects.create_superuser(
            username="revisor_auditoria",
            email="revisor@example.com",
            password="SenhaSomenteParaTeste123!",
        )

        self.categoria = Categoria.objects.create(nome="Literatura")

        self.curso = Curso.objects.create(
            nome="Sistemas de Informação",
        )

        self.membro = Membro.objects.create(
            nome_completo="Pessoa de Teste",
            tipo_membro="ADMIN",
            email="pessoa@example.com",
        )

        self.livro = Livro.objects.create(
            titulo="Livro de teste",
            categoria=self.categoria,
            qtd_total=3,
            qtd_disponivel=3,
        )

        self.emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
        )

        self.reserva = Reserva.objects.create(
            membro=self.membro,
            livro=self.livro,
        )

    def test_seis_modelos_possuem_historico_de_criacao(self):
        objetos = (
            self.categoria,
            self.curso,
            self.membro,
            self.livro,
            self.emprestimo,
            self.reserva,
        )

        for objeto in objetos:
            with self.subTest(modelo=type(objeto).__name__):
                criacao = objeto.history.filter(
                    history_type="+",
                ).first()

                self.assertIsNotNone(criacao)
                self.assertIsNotNone(criacao.history_date)
                self.assertEqual(criacao.id, objeto.pk)

    def test_alteracao_preserva_valor_anterior(self):
        self.categoria.nome = "Literatura brasileira"
        self.categoria.save()

        historico = self.categoria.history.order_by("history_id")

        self.assertEqual(historico.count(), 2)
        self.assertEqual(historico[0].nome, "Literatura")
        self.assertEqual(historico[1].nome, "Literatura brasileira")
        self.assertEqual(historico[1].history_type, "~")

    def test_exclusao_preserva_historico(self):
        categoria = Categoria.objects.create(nome="Categoria temporária")
        identificador = categoria.pk

        categoria.delete()

        historico = Categoria.history.filter(id=identificador)

        self.assertFalse(
            Categoria.objects.filter(pk=identificador).exists()
        )
        self.assertEqual(historico.count(), 2)
        self.assertTrue(
            historico.filter(history_type="-").exists()
        )

    def test_usuario_pode_ser_informado_fora_de_requisicao(self):
        self.reserva._history_user = self.usuario
        self.reserva.status = Reserva.Status.CANCELADA
        self.reserva.save()

        registro = self.reserva.history.latest()

        self.assertEqual(registro.status, Reserva.Status.CANCELADA)
        self.assertEqual(registro.history_user_id, self.usuario.pk)
        self.assertEqual(registro.history_type, "~")

    def test_operacao_sem_usuario_nao_inventa_responsavel(self):
        categoria = Categoria.objects.create(nome="Operação de sistema")

        self.assertIsNone(
            categoria.history.latest().history_user_id
        )

    def test_seis_admins_usam_simple_history_admin(self):
        modelos = (
            Categoria,
            Curso,
            Membro,
            Livro,
            Emprestimo,
            Reserva,
        )

        for modelo in modelos:
            with self.subTest(modelo=modelo.__name__):
                self.assertIsInstance(
                    admin.site._registry[modelo],
                    SimpleHistoryAdmin,
                )

    def test_admin_registra_usuario_ao_alterar_emprestimo(self):
        """Testa uma requisição real ao admin com usuário autenticado."""
        self.client.force_login(self.usuario)

        url = reverse(
            "admin:biblioteca_emprestimo_change",
            args=[self.emprestimo.pk],
        )

        # Obtém os valores atuais, incluindo o formato dos campos de data.
        pagina = self.client.get(url)
        self.assertEqual(pagina.status_code, 200)

        formulario = pagina.context["adminform"].form
        dados = {}

        for campo in formulario:
            if campo.name == "status":
                dados[campo.name] = "DEVOLVIDO"
                continue

            valor = campo.value()

            # O admin divide DateTimeField em data e horário.
            if isinstance(campo.field.widget, admin.widgets.AdminSplitDateTime):
                partes = campo.field.widget.decompress(valor)
                dados[f"{campo.name}_0"] = (
                    partes[0].strftime("%Y-%m-%d") if partes[0] else ""
                )
                dados[f"{campo.name}_1"] = (
                    partes[1].strftime("%H:%M:%S") if partes[1] else ""
                )
            elif hasattr(valor, "strftime"):
                dados[campo.name] = valor.strftime("%Y-%m-%d")
            else:
                dados[campo.name] = "" if valor is None else valor

        dados["_save"] = "Salvar"

        resposta = self.client.post(url, dados)

        self.assertEqual(resposta.status_code, 302)

        self.emprestimo.refresh_from_db()
        self.assertEqual(self.emprestimo.status, "DEVOLVIDO")

        registro = self.emprestimo.history.latest()

        self.assertEqual(registro.status, "DEVOLVIDO")
        self.assertEqual(registro.history_user_id, self.usuario.pk)
        self.assertIsNotNone(registro.history_date)

        # A atualização de estoque feita pelo empréstimo também é auditada.
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, 3)
        self.assertEqual(
            self.livro.history.latest().history_user_id,
            self.usuario.pk,
        )