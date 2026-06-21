from django.contrib import admin
from .models import Categoria, Autor, Livro, Membro, Emprestimo
from django.utils.html import mark_safe

# altera o título da aba do navegador (Title)
admin.site.site_title = "Biblioteca FLUI"

# altera o título do cabeçalho principal na página de login e no topo do painel (Header)
admin.site.site_header = "Biblioteca Comunitária FLUI"

# altera o texto de boas-vindas na página inicial do painel
admin.site.index_title = "Painel de Controle e Gestão"

@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'tipo_membro', 'ra', 'siape', 'email')
    list_filter = ('tipo_membro',)
    search_fields = ('nome_completo', 'ra', 'siape')
    
    fieldsets = [
        ('Informações Pessoais', {'fields': ['nome_completo', 'tipo_membro', 'email', 'telefone']}),
        ('Identificadores Acadêmicos', {'fields': ['ra', 'siape']}),
    ]

@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ('livro', 'membro', 'data_emprestimo', 'data_prevista_devolucao', 'status')
    list_filter = ('status', 'data_emprestimo')
    search_fields = ('membro__nome_completo', 'livro__titulo', 'membro__ra')

@admin.register(Livro)
class LivroAdmin(admin.ModelAdmin):
    fields = ('capa', 'image_preview', 'titulo', 'autores', 'categoria', 'qtd_total', 'qtd_disponivel', 'disponivel')
    
    readonly_fields = ('image_preview',) 

    list_display = ('titulo', 'image_preview', 'categoria', 'disponivel')

    def image_preview(self, obj):
        if obj.capa:
            return mark_safe(f'<img src="{obj.capa.url}" style="width: 90px; height: auto;" />')
        return "Sem imagem"
    
    image_preview.short_description = 'Capa'
    list_filter = ('disponivel', 'categoria')
    search_fields = ('titulo', 'autores__primeiro_nome', 'autores__sobrenome')

# registros padrão para tabelas mais simples
admin.site.register(Categoria)
admin.site.register(Autor)