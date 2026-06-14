from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User as AuthUser # Django's built-in User model
from datetime import timedelta # ⚠️ ADD THIS IMPORT AT THE TOP OF YOUR FILE
from django.core.exceptions import ValidationError


class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

class Autor(models.Model):
    primeiro_nome = models.CharField(max_length=50)
    sobrenome = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Autor"
        verbose_name_plural = "Autores" # This fixes "Autor

    def __str__(self):
        return f"{self.primeiro_nome} {self.sobrenome}"

class Editora(models.Model):
    primeiro_nome = models.CharField(max_length=50)
    sobrenome = models.CharField(max_length=50)
    def __str__(self):
        return f"{self.primeiro_nome} {self.sobrenome}"

class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    descricao = models.TextField()
    autores = models.ManyToManyField(Autor, related_name='Livros')
    editora = models.ForeignKey(Editora, on_delete=models.CASCADE, related_name='Livro')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='Livros')
    disponivel = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo

class Edicao(models.Model):
    livro = models.OneToOneField(Livro, on_delete=models.CASCADE, related_name='edition')
    numero_edicao = models.PositiveIntegerField()
    data_lancamento = models.DateField()
    paginas = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Edição"
        verbose_name_plural = "Edições" # This fixes "Edicaos"!

    def __str__(self):
        return f"{self.livro.titulo} - Edição {self.numero_edicao} ({self.data_lancamento.year})"

from django.core.exceptions import ValidationError # ⚠️ Import this at the top!

class Membro(models.Model):
    TIPOS_DE_MEMBRO = [
        ('ALUNO', 'Aluno'),
        ('PROFESSOR', 'Professor'),
        ('ADMIN', 'Administrador'),
    ]
    nome_completo = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    telefone = models.CharField(max_length=30, null=True, blank=True)
    tipo_membro = models.CharField(max_length=20, choices=TIPOS_DE_MEMBRO)

    ra = models.CharField(max_length=50, unique=True, null=True, blank=True)
    siape = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def clean(self):
        """
        Runs custom validation rules from the PDF specification.
        """
        super().clean()
        
        # --- STUDENT RULES ---
        if self.tipo_membro == 'ALUNO':
            # Rule 1: RA is mandatory for students
            if not self.ra:
                raise ValidationError({'ra': 'O campo RA é obrigatório para alunos.'})
            # Rule 2: Students CANNOT have a SIAPE[cite: 1]
            if self.siape:
                raise ValidationError({'siape': 'Alunos não podem possuir um número SIAPE.'})
        
        # --- PROFESSOR RULES ---
        if self.tipo_membro == 'PROFESSOR':
            # Rule 3: SIAPE is mandatory for professors[cite: 1]
            if not self.siape:
                raise ValidationError({'siape': 'O campo SIAPE é obrigatório para professores.'})
            # Rule 4: Professors CANNOT have an RA[cite: 1]
            if self.ra:
                raise ValidationError({'ra': 'Professores não podem possuir um número RA.'})

    def __str__(self):
        return f"{self.nome_completo} ({self.get_tipo_membro_display()})"

class Emprestimo(models.Model):
    STATUS_EMPRESTIMO = [
        #('SOLICITADO', 'Solicitado'),
        ('EMITIDO', 'Emitido'),
        ('DEVOLVIDO', 'Devolvido'),
        ('ATRASADO', 'Atrasado'),
        ('CANCELADO', 'Cancelado'),
    ]
    membro = models.ForeignKey(Membro, on_delete=models.CASCADE, related_name='livros_emprestados')
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name='livros_emprestados')
    edicao = models.ForeignKey(
        Edicao,
        on_delete=models.SET_NULL,
        related_name='livros_emprestados',
        null=True,
        blank=True
    )
    data_emprestimo = models.DateTimeField(default=timezone.now)
    data_prevista_devolucao = models.DateField(null=True, blank=True)
    data_devolucao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_EMPRESTIMO, default='EMITIDO')

    __original_status = None

    def clean(self): # previne que um livro nao seja emprestado se nao estiver disponivel
        super().clean()
        
        # We only check availability if this is a NEW loan transaction (self.pk is None)
        if self.pk is None and self.livro and not self.livro.disponivel:
            raise ValidationError({
                'livro': f"O livro '{self.livro.titulo}' não está disponível para empréstimo no momento."
            })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, *args, **kwargs):
        """
        Rule 2: Automatically calculate the due date before saving.
        """
        # Se o admin nao selecionar uma data de devolucao, a gente calcula automaticamente com base no tipo do membro
        if not self.data_prevista_devolucao and self.membro:
            # data_emprestimo é um DateTimeField, então convertemos o campo de data
            base_date = self.data_emprestimo.date() if self.data_emprestimo else timezone.now().date()
            
            if self.membro.tipo_membro == 'ALUNO':
                self.data_prevista_devolucao = base_date + timedelta(days=14)
            elif self.membro.tipo_membro == 'PROFESSOR':
                self.data_prevista_devolucao = base_date + timedelta(days=28)
            else:
                self.data_prevista_devolucao = base_date + timedelta(days=7) # Default for Admin


        super().save(*args, **kwargs)
        if self.status != self.__original_status:
            if self.status == 'EMITIDO':
                self.livro.disponivel = False
                self.livro.save(update_fields=['disponivel'])
            elif self.status in ['DEVOLVIDO', 'CANCELADO'] and self.__original_status == 'EMITIDO':
                if not Emprestimo.objects.filter(Livro=self.livro, status='EMITIDO').exists():
                    self.livro.disponivel = True
                    self.livro.save(update_fields=['disponivel'])
        self.__original_status = self.status

    class Meta:
        verbose_name = "Empréstimo"
        verbose_name_plural = "Empréstimos"

    def __str__(self):
        return f"{self.livro.titulo} emprestado para {self.membro.nome_completo} ({self.status})"