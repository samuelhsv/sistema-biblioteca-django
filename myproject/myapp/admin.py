from django.contrib import admin
from .models import Categoria, Autor, Editora, Livro, Edicao, Membro, Emprestimo

@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    list_display = ('nome_completo', 'tipo_membro', 'ra', 'siape', 'email')
    list_filter = ('tipo_membro',)
    search_fields = ('nome_completo', 'ra', 'siape')
    
    # Groups the fields nicely on the screen for the admin
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
    # What columns show up on the main books table
    list_display = ('titulo', 'categoria', 'editora', 'disponivel')
    
    # Sidebar filters to quickly isolate loaned or available stock[cite: 1]
    list_filter = ('disponivel', 'categoria', 'editora')
    
    # Search engine: Looks up by book title OR author's first/last name!
    search_fields = ('titulo', 'autores__primeiro_nome', 'autores__sobrenome')

# Standard registrations for simpler tables
admin.site.register(Categoria)
admin.site.register(Autor)
admin.site.register(Editora)
admin.site.register(Edicao)