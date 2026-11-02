from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
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
        professor = Membro(
            nome_completo="Carlos Silva",
            tipo_membro="PROFESSOR",
            siape="987",
        )
        professor.full_clean()

    def test_professor_com_curso_e_invalido(self):
        professor = Membro(
            nome_completo="Carlos Silva",
            tipo_membro="PROFESSOR",
            siape="987",
            curso=self.curso,
        )
        self.verificar_erro_no_campo(professor, "curso")

    def test_professor_com_periodo_e_invalido(self):
        professor = Membro(
            nome_completo="Carlos Silva",
            tipo_membro="PROFESSOR",
            siape="987",
            periodo=3,
        )
        self.verificar_erro_no_campo(professor, "periodo")

    def test_professor_sem_siape_e_invalido(self):
        professor = Membro(
            nome_completo="Carlos Silva",
            tipo_membro="PROFESSOR",
        )
        self.verificar_erro_no_campo(professor, "siape")

    def test_professor_com_ra_e_invalido(self):
        professor = Membro(
            nome_completo="Carlos Silva",
            tipo_membro="PROFESSOR",
            siape="987",
            ra="123",
        )
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

        # Simula exclusivamente um registro legado no banco.
        # update() contorna save(); não é o fluxo normal de cadastro.
        Membro.objects.filter(pk=aluno.pk).update(
            curso=None,
            periodo=None,
        )

        aluno.refresh_from_db()
        self.assertIsNone(aluno.curso)
        self.assertIsNone(aluno.periodo)

        # O registro continua consultável, mas não pode ser salvo
        # novamente enquanto os dados obrigatórios estiverem vazios.
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
        )
        self.assertIsNotNone(professor.pk)