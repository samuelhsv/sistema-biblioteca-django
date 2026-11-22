from datetime import timedelta

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.test import TestCase
from django.utils import timezone
from .models import Curso, Membro, Livro, Emprestimo
from django.core.management import call_command
from biblioteca.services import marcar_atrasados
from django.core import mail
from biblioteca.utils import enviar_email

from datetime import timedelta
from django.utils import timezone
from .models import Curso, Emprestimo, Livro, Membro


class MembroAlunoTests(TestCase):
    def setUp(self):
        self.curso = Curso.objects.create(
            nome="Sistemas de Informação"
        )

    def dados_aluno(self, **alteracoes):
        dados = {
            "nome_completo": "Ana Souza",
            "tipo_membro": "ALUNO",
            "ra": "123",
            "curso": self.curso,
            "periodo": 3,
        }
        dados.update(alteracoes)
        return dados

    def criar_aluno(self, **alteracoes):
        return Membro(**self.dados_aluno(**alteracoes))

    def criar_professor(self, **alteracoes):
        dados = {
            "nome_completo": "Carlos Silva",
            "tipo_membro": "PROFESSOR",
            "siape": "987",
            "email": "carlos@example.org",
        }
        dados.update(alteracoes)
        return Membro(**dados)

    def verificar_erro_no_campo(self, membro, campo):
        with self.assertRaises(ValidationError) as contexto:
            membro.full_clean()

        self.assertIn(campo, contexto.exception.message_dict)

    def test_aluno_completo_e_valido(self):
        aluno = self.criar_aluno()
        aluno.full_clean()
        aluno.save()

        aluno.refresh_from_db()
        self.assertEqual(aluno.curso, self.curso)
        self.assertEqual(aluno.periodo, 3)

    def test_aluno_sem_curso_e_invalido(self):
        aluno = self.criar_aluno(curso=None)
        self.verificar_erro_no_campo(aluno, "curso")

    def test_aluno_sem_periodo_e_invalido(self):
        aluno = self.criar_aluno(periodo=None)
        self.verificar_erro_no_campo(aluno, "periodo")

    def test_aluno_sem_ra_e_invalido(self):
        aluno = self.criar_aluno(ra=None)
        self.verificar_erro_no_campo(aluno, "ra")

    def test_aluno_com_siape_e_invalido(self):
        aluno = self.criar_aluno(siape="987")
        self.verificar_erro_no_campo(aluno, "siape")

    def test_periodo_fora_do_intervalo_e_invalido(self):
        for periodo in (0, 13):
            with self.subTest(periodo=periodo):
                aluno = self.criar_aluno(periodo=periodo)
                self.verificar_erro_no_campo(aluno, "periodo")

    def test_periodos_limite_sao_validos(self):
        for periodo in (1, 12):
            with self.subTest(periodo=periodo):
                aluno = self.criar_aluno(periodo=periodo)
                aluno.full_clean()

    def test_professor_sem_curso_e_periodo_e_valido(self):
        professor = self.criar_professor()
        professor.full_clean()

    def test_professor_com_curso_e_invalido(self):
        professor = self.criar_professor(curso=self.curso)
        self.verificar_erro_no_campo(professor, "curso")

    def test_professor_com_periodo_e_invalido(self):
        professor = self.criar_professor(periodo=3)
        self.verificar_erro_no_campo(professor, "periodo")

    def test_professor_sem_siape_e_invalido(self):
        professor = self.criar_professor(siape=None)
        self.verificar_erro_no_campo(professor, "siape")

    def test_professor_com_ra_e_invalido(self):
        professor = self.criar_professor(ra="123")
        self.verificar_erro_no_campo(professor, "ra")

    def test_administrador_nao_pode_ter_curso_ou_periodo(self):
        administrador = Membro(
            nome_completo="Maria Santos",
            tipo_membro="ADMIN",
            curso=self.curso,
            periodo=2,
        )

        with self.assertRaises(ValidationError) as contexto:
            administrador.full_clean()

        self.assertIn("curso", contexto.exception.message_dict)
        self.assertIn("periodo", contexto.exception.message_dict)

    def test_curso_com_aluno_nao_pode_ser_excluido(self):
        aluno = self.criar_aluno()
        aluno.save()

        with self.assertRaises(ProtectedError):
            self.curso.delete()

    def test_aluno_pendente_pode_ser_lido_e_completado(self):
        aluno = self.criar_aluno(ra="456")
        aluno.save()

        # Simula um registro legado.
        # update() contorna save() apenas para preparar este cenário.
        Membro.objects.filter(pk=aluno.pk).update(
            curso=None,
            periodo=None,
        )

        aluno.refresh_from_db()
        self.assertIsNone(aluno.curso)
        self.assertIsNone(aluno.periodo)

        with self.assertRaises(ValidationError):
            aluno.save()

        aluno.curso = self.curso
        aluno.periodo = 2
        aluno.save()

        aluno.refresh_from_db()
        self.assertEqual(aluno.curso, self.curso)
        self.assertEqual(aluno.periodo, 2)

    def test_save_rejeita_aluno_sem_curso_e_periodo(self):
        aluno = self.criar_aluno(
            curso=None,
            periodo=None,
        )

        with self.assertRaises(ValidationError) as contexto:
            aluno.save()

        self.assertIn("curso", contexto.exception.message_dict)
        self.assertIn("periodo", contexto.exception.message_dict)
        self.assertEqual(Membro.objects.count(), 0)

    def test_objects_create_rejeita_alunos_invalidos(self):
        casos = [
            ({"curso": None}, "curso"),
            ({"periodo": None}, "periodo"),
            ({"periodo": 0}, "periodo"),
            ({"periodo": 13}, "periodo"),
            ({"ra": None}, "ra"),
            ({"siape": "987"}, "siape"),
            ({"email": "email-invalido"}, "email"),
        ]

        for alteracoes, campo in casos:
            with self.subTest(alteracoes=alteracoes):
                with self.assertRaises(ValidationError) as contexto:
                    Membro.objects.create(
                        **self.dados_aluno(**alteracoes)
                    )

                self.assertIn(
                    campo,
                    contexto.exception.message_dict,
                )
                self.assertEqual(Membro.objects.count(), 0)

    def test_objects_create_salva_aluno_valido(self):
        aluno = Membro.objects.create(**self.dados_aluno())

        aluno.refresh_from_db()
        self.assertEqual(aluno.ra, "123")
        self.assertEqual(aluno.curso, self.curso)
        self.assertEqual(aluno.periodo, 3)
        self.assertEqual(Membro.objects.count(), 1)

    def test_save_rejeita_edicao_invalida_sem_alterar_banco(self):
        aluno = Membro.objects.create(**self.dados_aluno())
        aluno.periodo = 13

        with self.assertRaises(ValidationError) as contexto:
            aluno.save()

        self.assertIn("periodo", contexto.exception.message_dict)

        aluno.refresh_from_db()
        self.assertEqual(aluno.periodo, 3)

    def test_objects_create_valida_regras_do_professor(self):
        casos = [
            ({"siape": None}, "siape"),
            ({"ra": "123"}, "ra"),
            ({"curso": self.curso}, "curso"),
            ({"periodo": 3}, "periodo"),
        ]

        for alteracoes, campo in casos:
            with self.subTest(alteracoes=alteracoes):
                dados = {
                    "nome_completo": "Carlos Silva",
                    "tipo_membro": "PROFESSOR",
                    "siape": "987",
                    "email": "carlos@example.org",
                }
                dados.update(alteracoes)

                with self.assertRaises(ValidationError) as contexto:
                    Membro.objects.create(**dados)

                self.assertIn(
                    campo,
                    contexto.exception.message_dict,
                )
                self.assertEqual(Membro.objects.count(), 0)

        professor = Membro.objects.create(
            nome_completo="Carlos Silva",
            tipo_membro="PROFESSOR",
            siape="987",
            email="carlos@example.org",
        )
        self.assertIsNotNone(professor.pk)


class EmprestimoTests(TestCase):

    def setUp(self):
        self.curso = Curso.objects.create(
            nome="Sistemas de Informação"
        )

        self.membro = Membro.objects.create(
            nome_completo="Ana Souza",
            tipo_membro="ALUNO",
            ra="123",
            curso=self.curso,
            periodo=3,
        )

        self.livro = Livro.objects.create(
            titulo="Livro de Teste",
            qtd_total=5,
            qtd_disponivel=5,
        )

    def criar_emprestimo(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
        )
        self.livro.refresh_from_db()
        return emprestimo

    def test_emprestado_para_atrasado_nao_altera_estoque(self):
        emprestimo = self.criar_emprestimo()

        estoque_anterior = self.livro.qtd_disponivel

        emprestimo.status = "ATRASADO"
        emprestimo.save()

        self.livro.refresh_from_db()

        self.assertEqual(
            self.livro.qtd_disponivel,
            estoque_anterior
        )

    def test_atrasado_para_devolvido_devolve_unidade_ao_estoque(self):
        emprestimo = self.criar_emprestimo()

        emprestimo.status = "ATRASADO"
        emprestimo.save()

        estoque_anterior = self.livro.qtd_disponivel

        emprestimo.status = "DEVOLVIDO"
        emprestimo.save()

        self.livro.refresh_from_db()

        self.assertEqual(
            self.livro.qtd_disponivel,
            estoque_anterior + 1
        )

    def test_data_prevista_nao_e_recalculada_ao_salvar(self):
        emprestimo = self.criar_emprestimo()

        data_renovada = (
            timezone.localdate() + timedelta(days=30)
        )

        emprestimo.data_prevista_devolucao = data_renovada
        emprestimo.save()

        emprestimo.refresh_from_db()

        self.assertEqual(
            emprestimo.data_prevista_devolucao,
            data_renovada
        )
    def test_marcar_atrasados_atualiza_emprestimo_vencido(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            data_prevista_devolucao=timezone.localdate() - timedelta(days=1),
        )

        marcar_atrasados()

        emprestimo.refresh_from_db()
        self.assertEqual(emprestimo.status, "ATRASADO")

    def test_marcar_atrasados_nao_altera_emprestimo_no_prazo(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            data_prevista_devolucao=timezone.localdate() + timedelta(days=1),
        )

        marcar_atrasados()

        emprestimo.refresh_from_db()
        self.assertEqual(emprestimo.status, "EMPRESTADO")

    def test_marcar_atrasados_nao_altera_estoque(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            data_prevista_devolucao=timezone.localdate() - timedelta(days=1),
        )

        self.livro.refresh_from_db()
        estoque_anterior = self.livro.qtd_disponivel

        marcar_atrasados()

        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, estoque_anterior)

    def test_comando_atualizar_atrasos(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            data_prevista_devolucao=timezone.localdate() - timedelta(days=1),
        )

        call_command("atualizar_atrasos")

        emprestimo.refresh_from_db()
        self.assertEqual(emprestimo.status, "ATRASADO")

    def test_marcar_atrasados_nao_altera_emprestimo_que_vence_hoje(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            data_prevista_devolucao=timezone.localdate(),
        )

        marcar_atrasados()

        emprestimo.refresh_from_db()
        self.assertEqual(emprestimo.status, "EMPRESTADO")

    def test_devolvido_para_atrasado_e_devolvido_novamente_mantem_estoque(self):
        emprestimo = self.criar_emprestimo()
        estoque_emprestado = self.livro.qtd_disponivel

        emprestimo.status = "DEVOLVIDO"
        emprestimo.save()
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, estoque_emprestado + 1)

        emprestimo.status = "ATRASADO"
        emprestimo.save()
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, estoque_emprestado)

        emprestimo.status = "DEVOLVIDO"
        emprestimo.save()
        self.livro.refresh_from_db()
        self.assertEqual(self.livro.qtd_disponivel, estoque_emprestado + 1)

class MembroEmailTests(TestCase):
    def dados_professor(self, **alteracoes):
        dados = {
            "nome_completo": "Carlos da Silva",
            "tipo_membro": "PROFESSOR",
            "siape": "987",
            "email": "carlos@example.org",
        }
        dados.update(alteracoes)
        return dados

    def test_professor_sem_email_e_invalido(self):
        for email in (None, "", "   "):
            with self.subTest(email=email):
                professor = Membro(
                    **self.dados_professor(email=email)
                )

                with self.assertRaises(ValidationError) as contexto:
                    professor.save()

                self.assertIn(
                    "email",
                    contexto.exception.message_dict,
                )

        self.assertEqual(Membro.objects.count(), 0)

    def test_professor_precisa_de_nome_completo(self):
        for nome in (None, "", "   ", "Carlos"):
            with self.subTest(nome=nome):
                professor = Membro(
                    **self.dados_professor(nome_completo=nome)
                )

                with self.assertRaises(ValidationError) as contexto:
                    professor.save()

                self.assertIn(
                    "nome_completo",
                    contexto.exception.message_dict,
                )

        self.assertEqual(Membro.objects.count(), 0)

    def test_normaliza_nome_sem_alterar_capitalizacao(self):
        professor = Membro.objects.create(
            **self.dados_professor(
                nome_completo="  Carlos   da   Silva  "
            )
        )

        professor.refresh_from_db()
        self.assertEqual(
            professor.nome_completo,
            "Carlos da Silva",
        )

    def test_rejeita_formatos_invalidos_de_email(self):
        for email in (
            "sem-arroba",
            "carlos@",
            "@example.org",
            "carlos silva@example.org",
        ):
            with self.subTest(email=email):
                professor = Membro(
                    **self.dados_professor(email=email)
                )

                with self.assertRaises(ValidationError) as contexto:
                    professor.save()

                self.assertIn(
                    "email",
                    contexto.exception.message_dict,
                )

        self.assertEqual(Membro.objects.count(), 0)

    def test_normaliza_email_antes_de_validar_e_salvar(self):
        professor = Membro.objects.create(
            **self.dados_professor(
                email="  Carlos@EXAMPLE.ORG  "
            )
        )

        professor.refresh_from_db()
        self.assertEqual(
            professor.email,
            "carlos@example.org",
        )

    def test_rejeita_email_duplicado_com_maiusculas(self):
        Membro.objects.create(**self.dados_professor())

        with self.assertRaises(ValidationError) as contexto:
            Membro.objects.create(
                **self.dados_professor(
                    nome_completo="Outra Professora",
                    siape="654",
                    email="CARLOS@EXAMPLE.ORG",
                )
            )

        self.assertIn("email", contexto.exception.message_dict)
        self.assertEqual(Membro.objects.count(), 1)

    def test_detecta_duplicado_em_registro_legado(self):
        professor = Membro.objects.create(
            **self.dados_professor()
        )

        # Simula um e-mail antigo ainda não normalizado.
        Membro.objects.filter(pk=professor.pk).update(
            email="CARLOS@EXAMPLE.ORG"
        )

        with self.assertRaises(ValidationError) as contexto:
            Membro.objects.create(
                **self.dados_professor(
                    nome_completo="Outra Professora",
                    siape="654",
                    email="carlos@example.org",
                )
            )

        self.assertIn("email", contexto.exception.message_dict)
        self.assertEqual(Membro.objects.count(), 1)

    def test_edicao_preserva_email_do_proprio_membro(self):
        professor = Membro.objects.create(
            **self.dados_professor()
        )
        professor.nome_completo = "Carlos da Silva Souza"
        professor.save()

        professor.refresh_from_db()
        self.assertEqual(
            professor.email,
            "carlos@example.org",
        )
        self.assertEqual(
            professor.nome_completo,
            "Carlos da Silva Souza",
        )

    def test_edicao_rejeita_email_de_outro_membro(self):
        Membro.objects.create(**self.dados_professor())

        outro = Membro.objects.create(
            **self.dados_professor(
                nome_completo="Outra Professora",
                siape="654",
                email="outra@example.org",
            )
        )

        outro.email = "CARLOS@EXAMPLE.ORG"

        with self.assertRaises(ValidationError) as contexto:
            outro.save()

        self.assertIn("email", contexto.exception.message_dict)

        outro.refresh_from_db()
        self.assertEqual(outro.email, "outra@example.org")

    def test_permite_varios_membros_sem_email(self):
        curso = Curso.objects.create(
            nome="Engenharia de Software"
        )

        aluno = Membro.objects.create(
            nome_completo="Ana Souza",
            tipo_membro="ALUNO",
            ra="123",
            curso=curso,
            periodo=2,
            email=None,
        )

        administrador = Membro.objects.create(
            nome_completo="Maria Santos",
            tipo_membro="ADMIN",
            email=None,
        )

        aluno.refresh_from_db()
        administrador.refresh_from_db()

        self.assertIsNone(aluno.email)
        self.assertIsNone(administrador.email)
        self.assertEqual(
            Membro.objects.filter(email__isnull=True).count(),
            2,
        )

    def test_email_vazio_e_salvo_como_null(self):
        for email in ("", "   "):
            with self.subTest(email=email):
                membro = Membro.objects.create(
                    nome_completo="Maria Santos",
                    tipo_membro="ADMIN",
                    email=email,
                )

                membro.refresh_from_db()
                self.assertIsNone(membro.email)

    def test_banco_impede_duplicidade_exata(self):
        primeiro = Membro.objects.create(
            **self.dados_professor()
        )
        segundo = Membro.objects.create(
            **self.dados_professor(
                nome_completo="Outra Professora",
                siape="654",
                email="outra@example.org",
            )
        )

        # update() não chama save(), mas a restrição unique
        # do banco ainda impede duplicidade exata.
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Membro.objects.filter(pk=segundo.pk).update(
                    email=primeiro.email
                )

        segundo.refresh_from_db()
        self.assertEqual(
            segundo.email,
            "outra@example.org",
        )

    def test_formulario_apresenta_erros_nos_campos(self):
        FormularioMembro = modelform_factory(
            Membro,
            fields=[
                "nome_completo",
                "tipo_membro",
                "siape",
                "email",
            ],
        )

        formulario = FormularioMembro(
            data={
                "nome_completo": "Carlos",
                "tipo_membro": "PROFESSOR",
                "siape": "987",
                "email": "",
            }
        )

        self.assertFalse(formulario.is_valid())
        self.assertIn("nome_completo", formulario.errors)
        self.assertIn("email", formulario.errors)


class AutenticacaoTests(TestCase):
    def setUp(self):
        self.usuario = User.objects.create_user(
            username="123",
            email="ana@email.com",
            password="senha123",
        )

    def test_login_com_credenciais_corretas(self):
        resposta = self.client.post(
            "/contas/login/",
            {
                "username": "123",
                "password": "senha123",
            },
        )

        self.assertEqual(resposta.status_code, 302)
        self.assertTrue(resposta.wsgi_request.user.is_authenticated)

    def test_login_com_senha_incorreta(self):
        resposta = self.client.post(
            "/contas/login/",
            {
                "username": "123",
                "password": "senhaerrada",
            },
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(resposta.wsgi_request.user.is_authenticated)

    def test_usuario_sem_membro_acessa_pagina_inicial(self):
        self.client.force_login(self.usuario)

        resposta = self.client.get("/")

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(
            resposta,
            "Sua conta não possui um membro vinculado.",
        )
        self.assertTrue(resposta.wsgi_request.user.is_authenticated)

    def test_logout_desconecta_usuario(self):
        self.client.force_login(self.usuario)

        resposta = self.client.post("/contas/logout/")

        self.assertEqual(resposta.status_code, 302)
        self.assertFalse(resposta.wsgi_request.user.is_authenticated)

class EmailTests(TestCase):
    def test_envia_email(self):
        enviar_email(
            "Teste",
            "emails/teste.txt",
            {
                "nome": "Usuário de teste",
            },
            "email@exemplo.com"
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["email@exemplo.com"])

    def test_assunto_correto(self):
        enviar_email(
            "Teste FLUI",
            "emails/teste.txt",
            {
                "nome": "Usuário de teste",
            },
            "email@exemplo.com"
        )

        self.assertEqual(mail.outbox[0].subject, "Teste FLUI")

    def test_template_incluido_no_email(self):
        enviar_email(
            "Teste",
            "emails/teste.txt",
            {
                "nome": "Usuário de teste",
            },
            "email@exemplo.com"
        )

        self.assertIn("Olá, Usuário de teste!", mail.outbox[0].body)
        self.assertIn("Este é um e-mail de teste", mail.outbox[0].body)
        self.assertIn("Biblioteca FLUI", mail.outbox[0].body)
        
class BloqueioEmprestimoPendenciaTests(TestCase):
    def setUp(self):
        self.curso = Curso.objects.create(nome="Ciência da Computação")
        self.membro = Membro.objects.create(
            nome_completo="Ana Souza",
            tipo_membro="ALUNO",
            ra="12345",
            curso=self.curso,
            periodo=4,
        )
        self.livro = Livro.objects.create(
            titulo="Clean Code",
            qtd_total=3,
            qtd_disponivel=3,
        )
        self.outro_livro = Livro.objects.create(
            titulo="Domain-Driven Design",
            qtd_total=3,
            qtd_disponivel=3,
        )

    def test_membro_com_emprestimo_atrasado_nao_consegue_novo_emprestimo(self):
        Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            status="ATRASADO",
            data_prevista_devolucao=timezone.localdate() - timedelta(days=2),
        )

        self.assertTrue(self.membro.possui_pendencia())

        novo = Emprestimo(membro=self.membro, livro=self.outro_livro)
        with self.assertRaises(ValidationError) as ctx:
            novo.full_clean()

        self.assertIn("membro", ctx.exception.message_dict)

    def test_membro_com_emprestimo_vencido_ainda_emprestado_nao_consegue_novo_emprestimo(self):
        Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            status="EMPRESTADO",
            data_prevista_devolucao=timezone.localdate() - timedelta(days=1),
        )

        self.assertTrue(self.membro.possui_pendencia())

        novo = Emprestimo(membro=self.membro, livro=self.outro_livro)
        with self.assertRaises(ValidationError) as ctx:
            novo.full_clean()

        self.assertIn("membro", ctx.exception.message_dict)

    def test_membro_regular_consegue_novo_emprestimo(self):
        self.assertFalse(self.membro.possui_pendencia())

        emprestimo = Emprestimo(membro=self.membro, livro=self.livro)
        emprestimo.full_clean()
        emprestimo.save()

        self.assertEqual(Emprestimo.objects.count(), 1)

    def test_devolver_livro_atrasado_continua_permitido_e_libera_bloqueio(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            status="ATRASADO",
            data_prevista_devolucao=timezone.localdate() - timedelta(days=2),
        )
        self.assertTrue(self.membro.possui_pendencia())

        emprestimo.status = "DEVOLVIDO"
        emprestimo.data_devolucao = timezone.localdate()
        emprestimo.full_clean()
        emprestimo.save()

        self.assertFalse(self.membro.possui_pendencia())

        novo = Emprestimo(membro=self.membro, livro=self.outro_livro)
        novo.full_clean()
        novo.save()
        self.assertEqual(Emprestimo.objects.count(), 2)

    def test_emprestimo_com_vencimento_hoje_nao_e_pendencia(self):
        Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            status="EMPRESTADO",
            data_prevista_devolucao=timezone.localdate(),
        )

        self.assertFalse(self.membro.possui_pendencia())

    def test_editar_data_de_emprestimo_atrasado_sem_alterar_status(self):
        emprestimo = Emprestimo.objects.create(
            membro=self.membro,
            livro=self.livro,
            status="ATRASADO",
            data_prevista_devolucao=timezone.localdate() - timedelta(days=2),
        )

        emprestimo.data_prevista_devolucao = (
            timezone.localdate() - timedelta(days=3)
        )

        emprestimo.full_clean()

        self.assertEqual(emprestimo.status, "ATRASADO")