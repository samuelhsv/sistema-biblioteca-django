from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models.deletion import ProtectedError
from django.forms import modelform_factory
from django.test import TestCase

from .models import Curso, Membro


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