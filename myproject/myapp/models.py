from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User as AuthUser # Django's built-in User model



class Categoria(models.Model):
    nome = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return self.nome

class Autor(models.Model):
    primeiro_nome = models.CharField(max_length=50)
    sobrenome = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Autor"
        verbose_name_plural = "Autores" # 👈 This fixes "Autor

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
    
    '''
    # --- COVER IMAGE FIELD ADDED ---
    cover_image = models.ImageField(
        upload_to='Livro_covers/', 
        null=True,                 # Imag   e is optional
        blank=True                 # Also optional in forms
    )
    '''

    def __str__(self):
        return self.titulo

class Edicao(models.Model):
    livro = models.OneToOneField(Livro, on_delete=models.CASCADE, related_name='edition')
    numero_edicao = models.PositiveIntegerField()
    data_lancamento = models.DateField()
    paginas = models.PositiveIntegerField()

    class Meta:
        verbose_name = "Edição"
        verbose_name_plural = "Edições" # 👈 This fixes "Edicaos"!

    def __str__(self):
        return f"{self.livro.titulo} - Edição {self.numero_edicao} ({self.data_lancamento.year})"

from django.core.exceptions import ValidationError # ⚠️ Import this at the top!

class Membro(models.Model):
    TIPOS_DE_MEMBRO = [
        ('ALUNO', 'Aluno'),
        ('PROFESSOR', 'Professor'), # Updated to match your PDF spec
        ('ADMIN', 'Administrador'),
    ]
    usuario = models.OneToOneField(AuthUser, on_delete=models.CASCADE, related_name='member')
    tipo_membro = models.CharField(max_length=20, choices=TIPOS_DE_MEMBRO)
    
    # Optional in DB layer because they depend on the member type
    ra = models.CharField(max_length=50, unique=True, null=True, blank=True)
    siape = models.CharField(max_length=50, unique=True, null=True, blank=True)

    def clean(self):
        """
        Runs custom validation rules from the PDF specification.
        """
        super().clean()
        
        # Rule 1: If student, RA is mandatory
        if self.tipo_membro == 'ALUNO' and not self.ra:
            raise ValidationError({'ra': 'O campo RA é obrigatório para alunos.'})
        
        # Rule 2: If professor, SIAPE is mandatory
        if self.tipo_membro == 'PROFESSOR' and not self.siape:
            raise ValidationError({'siape': 'O campo SIAPE é obrigatório para professores.'})

    def __str__(self):
        return f"{self.usuario.username} ({self.get_tipo_membro_display()})"

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__original_status = self.status

    def save(self, *args, **kwargs):
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

    def __str__(self):
        return f"{self.livro.titulo} emprestado para {self.membro.usuario.username} ({self.status})"