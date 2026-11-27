from django.db import models
from django.conf import settings
from django.db import models

class Conferencia(models.Model):
    iniciada_em = models.DateTimeField(auto_now_add=True)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    finalizada = models.BooleanField(default=False)
    observacoes = models.TextField(blank=True)

class ItemConferencia(models.Model):
    conferencia = models.ForeignKey(Conferencia, on_delete=models.CASCADE, related_name="itens")
    livro = models.ForeignKey("biblioteca.Livro", on_delete=models.PROTECT)
    qtd_esperada = models.PositiveIntegerField()
    qtd_encontrada = models.PositiveIntegerField(null=True, blank=True)

    @property
    def diferenca(self):
        if self.qtd_encontrada is None:
            return None
        return self.qtd_encontrada - self.qtd_esperada