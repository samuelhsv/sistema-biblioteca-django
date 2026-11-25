from datetime import timedelta

from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models, router, transaction
from django.utils import timezone
from simple_history.models import HistoricalRecords


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    history = HistoricalRecords()

    def __str__(self):
        return self.nome


class Autor(models.Model):
    primeiro_nome = models.CharField(max_length=50)
    sobrenome = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Autor"
        verbose_name_plural = "Autores"

    def __str__(self):
        return f"{self.primeiro_nome} {self.sobrenome}"


class Livro(models.Model):
    titulo = models.CharField(max_length=200)

    capa = models.ImageField(
        upload_to="media/images",
        null=True,
        blank=True,
    )

    autores = models.ManyToManyField(
        Autor,
        related_name="Livros",
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.SET_NULL,
        null=True,
        related_name="Livros",
    )

    qtd_total = models.PositiveIntegerField(
        default=1,
        verbose_name="quantidade total",
    )

    qtd_disponivel = models.PositiveIntegerField(
        default=1,
        verbose_name="quantidade disponível",
    )

    disponivel = models.BooleanField(default=True)

    history = HistoricalRecords()

    @property
    def qtd_livre_para_reserva(self):
        """
        Retorna quantos exemplares podem receber novas reservas.

        Reservas aguardando retirada seguram exemplares, mas não
        alteram a quantidade física registrada em qtd_disponivel.
        """
        # Import local evita importação circular entre os apps.
        from reservas.models import Reserva

        aguardando_retirada = self.reservas.filter(
            status=Reserva.Status.AGUARDANDO_RETIRADA
        ).count()

        return max(
            self.qtd_disponivel - aguardando_retirada,
            0,
        )

    def __str__(self):
        return self.titulo


class Curso(models.Model):
    nome = models.CharField(max_length=100, unique=True)

    history = HistoricalRecords()

    class Meta:
        ordering = ["nome"]
        verbose_name = "Curso"
        verbose_name_plural = "Cursos"

    def __str__(self):
        return self.nome


class Membro(models.Model):
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="membro",
    )
    TIPOS_DE_MEMBRO = [
        ("ALUNO", "Aluno"),
        ("PROFESSOR", "Professor"),
        ("ADMIN", "Administrador"),
    ]

    nome_completo = models.CharField(
        max_length=255,
        null=True,
        blank=True,
    )

    email = models.EmailField(
        "e-mail",
        max_length=255,
        unique=True,
        null=True,
        blank=True,
    )

    telefone = models.CharField(
        max_length=30,
        null=True,
        blank=True,
    )

    tipo_membro = models.CharField(
        max_length=20,
        choices=TIPOS_DE_MEMBRO,
    )

    ra = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    siape = models.CharField(
        max_length=50,
        unique=True,
        null=True,
        blank=True,
    )

    curso = models.ForeignKey(
        "Curso",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="alunos",
    )

    periodo = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(12),
        ],
        help_text="Período atual do aluno (1 a 12)",
        verbose_name="período",
    )

    history = HistoricalRecords()

    def _normalizar_dados(self):
        """
        Remove espaços nas extremidades e padroniza o e-mail.

        E-mail vazio vira None, permitindo vários membros sem e-mail
        nos perfis em que o preenchimento não é obrigatório.
        """
        self.email = (self.email or "").strip().lower() or None

        # Remove espaços extras sem alterar maiúsculas e minúsculas.
        self.nome_completo = (
            " ".join((self.nome_completo or "").split()) or None
        )

    def clean_fields(self, exclude=None):
        """
        Normaliza antes da validação individual dos campos.

        Isso evita rejeitar um e-mail válido apenas porque foi
        informado com espaços nas extremidades.
        """
        self._normalizar_dados()
        super().clean_fields(exclude=exclude)
        

    def clean(self):
        """Valida as regras dos perfis e a duplicidade de e-mail."""
        super().clean()

        # Também normaliza caso clean() seja chamado diretamente.
        self._normalizar_dados()
        erros = {}

        if self.tipo_membro == "ALUNO":
            if not self.ra:
                erros["ra"] = "O campo RA é obrigatório para alunos."

            if self.siape:
                erros["siape"] = (
                    "Alunos não podem possuir um número SIAPE."
                )

            if not self.curso_id:
                erros["curso"] = "Alunos precisam informar o curso."

            if self.periodo is None:
                erros["periodo"] = "Alunos precisam informar o período."

        else:
            if self.curso_id is not None:
                erros["curso"] = "Somente alunos têm curso."

            if self.periodo is not None:
                erros["periodo"] = "Somente alunos têm período."

            if self.tipo_membro == "PROFESSOR":
                if not self.siape:
                    erros["siape"] = (
                        "O campo SIAPE é obrigatório para professores."
                    )

                if self.ra:
                    erros["ra"] = (
                        "Professores não podem possuir um número RA."
                    )

                if not self.email:
                    erros["email"] = (
                        "Professores precisam informar o e-mail."
                    )

                if len((self.nome_completo or "").split()) < 2:
                    erros["nome_completo"] = (
                        "Informe o nome completo do professor "
                        "com pelo menos duas palavras."
                    )

        if self.email:
            duplicados = (
                type(self)
                .objects.filter(email__iexact=self.email)
                .exclude(pk=self.pk)
            )

            if duplicados.exists():
                erros["email"] = (
                    "Este e-mail já está cadastrado para outro membro."
                )

        if erros:
            raise ValidationError(erros)

    def save(self, *args, **kwargs):
        """
        Valida antes de salvar, inclusive em objects.create().

        update() e bulk_create() não executam este método.
        """
        self.full_clean()
        return super().save(*args, **kwargs)

    def possui_pendencia(self):
        hoje = timezone.localdate()

        return self.livros_emprestados.filter(
            models.Q(status="ATRASADO")
            | models.Q(
                status="EMPRESTADO",
                data_prevista_devolucao__lt=hoje,
            )
        ).exists()


    def __str__(self):
        return (
            f"{self.nome_completo} "
            f"({self.get_tipo_membro_display()})"
        )


class Emprestimo(models.Model):
    STATUS_EMPRESTIMO = [
        ("EMPRESTADO", "Emprestado"),
        ("DEVOLVIDO", "Devolvido"),
        ("ATRASADO", "Atrasado"),
    ]

    membro = models.ForeignKey(
        Membro,
        on_delete=models.CASCADE,
        related_name="livros_emprestados",
    )

    livro = models.ForeignKey(
        Livro,
        on_delete=models.CASCADE,
        related_name="livros_emprestados",
    )

    data_emprestimo = models.DateTimeField(default=timezone.now)

    data_prevista_devolucao = models.DateField(
        null=True,
        blank=True,
    )

    data_devolucao = models.DateField(
        null=True,
        blank=True,
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_EMPRESTIMO,
        default="EMPRESTADO",
    )

    qtd_renovacoes = models.PositiveSmallIntegerField(default=0)

    def prazo_do_perfil(self):
        return {
            "ALUNO": 14,
            "PROFESSOR": 28,
        }.get(self.membro.tipo_membro, 7)

    def pode_renovar(self):
        if self.status != "EMPRESTADO":
            return False, "Somente empréstimos ativos podem ser renovados."
    
        if self.membro.possui_pendencia():
            return False, "Você possui pendências e não pode renovar empréstimos."
    
        if self.livro.reservas.filter(status="NA_FILA").exists():
            return False, "Este livro possui pessoas na fila de espera."
    
        limite = self.data_emprestimo.date() + timedelta(
            days=settings.BIBLIOTECA_LIMITE_TOTAL_DIAS
        )
    
        if self.data_prevista_devolucao >= limite:
            return False, "Este empréstimo já atingiu o limite máximo de 30 dias."
    
        return True, ""
    
    
    def renovar(self):
        pode, motivo = self.pode_renovar()
    
        if not pode:
            raise ValidationError(motivo)
    
        limite = self.data_emprestimo.date() + timedelta(
            days=settings.BIBLIOTECA_LIMITE_TOTAL_DIAS
        )
    
        nova_data = min(
            self.data_prevista_devolucao + timedelta(days=self.prazo_do_perfil()),
            limite,
        )
    
        self.data_prevista_devolucao = nova_data
        self.qtd_renovacoes += 1
    
        self.save(
            update_fields=["data_prevista_devolucao", "qtd_renovacoes"]
        )

    history = HistoricalRecords()

    def clean(self):
        """Valida estoque, reservas e pendências de novos empréstimos."""
        super().clean()
        if not self._state.adding or self.status not in {"EMPRESTADO", "ATRASADO"}:
            return

        erros = {}
        if self.livro_id:
            livro = self.livro
            if not livro.disponivel or livro.qtd_disponivel <= 0:
                erros["livro"] = "O livro não está disponível para empréstimo."
            elif livro.qtd_livre_para_reserva <= 0:
                erros["livro"] = (
                    "Todos os exemplares disponíveis estão reservados para a fila."
                )

        if self.membro_id:
            pendencias = type(self).objects.filter(membro_id=self.membro_id).filter(
                models.Q(status="ATRASADO")
                | models.Q(
                    status="EMPRESTADO",
                    data_prevista_devolucao__lt=timezone.localdate(),
                )
            )

        if pendencias.exists():
                erros["membro"] = (
                    "O membro possui devolução pendente e não pode realizar "
                    "um novo empréstimo."
                )

        if erros:
            raise ValidationError(erros)

    def save(self, *, force_insert=False, force_update=False,
             using=None, update_fields=None):
        if update_fields is not None:
            update_fields = frozenset(update_fields)
            if not update_fields:
                return

        banco = using or router.db_for_write(type(self), instance=self)
        ativos = {"EMPRESTADO", "ATRASADO"}

        if not self.data_prevista_devolucao and self.membro_id:
            base_date = (self.data_emprestimo or timezone.now()).date()
            self.data_prevista_devolucao = (
                base_date + timedelta(days=self.prazo_do_perfil())
            )

        with transaction.atomic(using=banco):
            anterior = None
            if self.pk is not None:
                anterior = (
                    type(self).objects.using(banco).select_for_update()
                    .filter(pk=self.pk).values_list("status", flat=True).first()
                )

            status_salvo = self.status
            if update_fields is not None and "status" not in update_fields:
                status_salvo = anterior

            retirar = status_salvo in ativos and anterior not in ativos
            repor = status_salvo == "DEVOLVIDO" and anterior in ativos

            if retirar or repor:
                livro = (
                    Livro.objects.using(banco).select_for_update()
                    .get(pk=self.livro_id)
                )
                if retirar:
                    if not livro.disponivel or livro.qtd_disponivel <= 0:
                        raise ValidationError(
                            {"livro": "O livro não está disponível para empréstimo."}
                        )
                    if livro.qtd_livre_para_reserva <= 0:
                        raise ValidationError(
                            {"livro": "Todos os exemplares disponíveis estão reservados para a fila."}
                        )
                    if livro.qtd_livre_para_reserva <= 0:
                        raise ValidationError(
                            {"livro": "Todos os exemplares disponíveis estão reservados para a fila."}
                        )
                    livro.qtd_disponivel -= 1
                else:
                    livro.qtd_disponivel = min(
                        livro.qtd_total, livro.qtd_disponivel + 1
                    )

                livro.disponivel = livro.qtd_disponivel > 0
                livro.save(
                    using=banco,
                    update_fields=["qtd_disponivel", "disponivel"],
                )

            super().save(
                force_insert=force_insert,
                force_update=force_update,
                using=banco,
                update_fields=update_fields,
            )

    class Meta:
        verbose_name = "Empréstimo"
        verbose_name_plural = "Empréstimos"

    def __str__(self):
        return (
            f"{self.livro.titulo} emprestado para "
            f"{self.membro.nome_completo} ({self.status})"
        )

