from django.contrib import admin
from .models import Conferencia, ItemConferencia
from django.utils.html import format_html
from biblioteca.models import Livro
from django.urls import reverse

class ItemConferenciaInline(admin.TabularInline):
    model = ItemConferencia
    extra = 0
    fields = ("livro", "qtd_esperada", "qtd_encontrada", "mostrar_diferenca")
    readonly_fields = ("livro", "qtd_esperada", "mostrar_diferenca")

    def has_change_permission(self, request, obj=None):
      if obj and obj.finalizada:
        return False
      return super().has_change_permission(request, obj)

    def has_add_permission(self, request, obj=None):
      if obj and obj.finalizada:
        return False
      return super().has_add_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
     if obj and obj.finalizada:
       return False
     return super().has_delete_permission(request, obj)

    def mostrar_diferenca(self, obj):
      diferenca = obj.diferenca

      if diferenca is None:
        return "Não conferido"

      if diferenca != 0:
        return format_html(
            '<span style="color: red; font-weight: bold;">{}</span>',
            diferenca
        )

      return diferenca
 
    mostrar_diferenca.short_description = "Diferença"

@admin.register(Conferencia)
class ConferenciaAdmin(admin.ModelAdmin):
     inlines = [ItemConferenciaInline]
     list_display = ("id", "iniciada_em", "responsavel", "finalizada", "link_relatorio")

     def link_relatorio(self, obj):
      url = reverse(
        "inventario:relatorio_divergencias",
        args=[obj.id]
    )
      return format_html('<a href="{}">Ver relatório</a>', url)

     link_relatorio.short_description = "Relatório"
     actions = ["gerar_itens_acervo"]

     @admin.action(description="Gerar itens a partir do acervo")
     def gerar_itens_acervo(self, request, queryset):
      total = 0
      for conferencia in queryset:
        if conferencia.finalizada:
         continue

        for livro in Livro.objects.all():

            item, criado = ItemConferencia.objects.get_or_create(
                conferencia=conferencia,
                livro=livro,
                defaults={
                    "qtd_esperada": livro.qtd_disponivel
                }
            )

            if criado:
                total += 1

      self.message_user(
        request,
        f"{total} itens foram gerados com sucesso."
    )
     def save_model(self, request, obj, form, change):
      if not change:
          obj.responsavel = request.user
      super().save_model(request, obj, form, change)
             
     def get_readonly_fields(self, request, obj=None):
      if obj and obj.finalizada:
         return ("iniciada_em", "responsavel", "finalizada", "observacoes")
      return ("iniciada_em", "responsavel")

      