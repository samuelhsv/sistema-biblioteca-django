from django.db import models
from django.utils import timezone
from django.utils.safestring import mark_safe
from datetime import timedelta
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
        verbose_name_plural = "Autores"

    def __str__(self):
        return f"{self.primeiro_nome} {self.sobrenome}"
    
class Livro(models.Model):
    titulo = models.CharField(max_length=200)
    capa = models.ImageField(upload_to="media/images", null=True, blank=True)
    autores = models.ManyToManyField(Autor, related_name='Livros')
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='Livros')
    qtd_total = models.PositiveIntegerField(default=1, verbose_name="quantidade total")
    qtd_disponivel = models.PositiveIntegerField(default=1, verbose_name="quantidade disponível")
    disponivel = models.BooleanField(default=True)

    def __str__(self):
        return self.titulo
        
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
        super().clean()
        
        if self.tipo_membro == 'ALUNO':
            if not self.ra:
                raise ValidationError({'ra': 'O campo RA é obrigatório para alunos.'})
            if self.siape:
                raise ValidationError({'siape': 'Alunos não podem possuir um número SIAPE.'})
        
        if self.tipo_membro == 'PROFESSOR':
            if not self.siape:
                raise ValidationError({'siape': 'O campo SIAPE é obrigatório para professores.'})
            if self.ra:
                raise ValidationError({'ra': 'Professores não podem possuir um número RA.'})

    def __str__(self):
        return f"{self.nome_completo} ({self.get_tipo_membro_display()})"

class Emprestimo(models.Model):
    STATUS_EMPRESTIMO = [
        ('EMPRESTADO', 'Emprestado'),
        ('DEVOLVIDO', 'Devolvido'),
        ('ATRASADO', 'Atrasado'),
    ]
    membro = models.ForeignKey(Membro, on_delete=models.CASCADE, related_name='livros_emprestados')
    livro = models.ForeignKey(Livro, on_delete=models.CASCADE, related_name='livros_emprestados')
    data_emprestimo = models.DateTimeField(default=timezone.now)
    data_prevista_devolucao = models.DateField(null=True, blank=True)
    data_devolucao = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_EMPRESTIMO, default='EMPRESTADO')

    __original_status = None

    def clean(self):
        super().clean()
        
        if self.pk is None and self.livro and not self.livro.disponivel:
            raise ValidationError({
                'livro': f"O livro '{self.livro.titulo}' não está disponível para empréstimo no momento."
            })

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Se o ID (pk) é None, o livro está sendo criado agora
        if self.pk is None:
            self.__original_status = None
        else:
            self.__original_status = self.status

    def save(self, *args, **kwargs):
        if not self.data_prevista_devolucao and self.membro:
            base_date = self.data_emprestimo.date() if self.data_emprestimo else timezone.now().date()
            
            if self.membro.tipo_membro == 'ALUNO':
                self.data_prevista_devolucao = base_date + timedelta(days=14)
            elif self.membro.tipo_membro == 'PROFESSOR':
                self.data_prevista_devolucao = base_date + timedelta(days=28)
            else:
                self.data_prevista_devolucao = base_date + timedelta(days=7)

        # salva o empréstimo primeiro para garantir a consistência
        super().save(*args, **kwargs)
        
        if self.status != self.__original_status:
            if self.status == 'EMPRESTADO':
                self.livro.qtd_disponivel -= 1
                if self.livro.qtd_disponivel <= 0: 
                    self.livro.disponivel = False              
                    self.livro.save(update_fields=['qtd_disponivel', 'disponivel'])
                else:
                    self.livro.save(update_fields=['qtd_disponivel'])                   
            
            elif self.status == 'DEVOLVIDO' and self.__original_status == 'EMPRESTADO': 
                self.livro.disponivel = True
                self.livro.qtd_disponivel = min(self.livro.qtd_total, self.livro.qtd_disponivel + 1)
                self.livro.save(update_fields=['qtd_disponivel', 'disponivel'])
                
        # atualiza o estado original na memória para evitar execuções duplicadas caso salve de novo
        self.__original_status = self.status

    class Meta:
        verbose_name = "Empréstimo"
        verbose_name_plural = "Empréstimos"

    def __str__(self):
        return f"{self.livro.titulo} emprestado para {self.membro.nome_completo} ({self.status})"