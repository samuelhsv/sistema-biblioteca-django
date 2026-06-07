from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User as AuthUser
from django.utils import timezone # timezone import kiya
from datetime import timedelta    # timedelta import kiya
from django.contrib import messages # messages import kiya


from .models import Categoria, Autor, Editora, Livro, Edicao, Membro, Emprestimo



class MembroInline(admin.StackedInline):
    model = Membro
    can_delete = False
    verbose_name_plural = 'Member Profile'
    fk_name = 'usuario'

class CustomUserAdmin(BaseUserAdmin):
    inlines = (MembroInline, )
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'get_member_type_display_for_admin')
    list_select_related = ('member',)

    def get_member_type_display_for_admin(self, instance):
        try:
            if hasattr(instance, 'member') and instance.member:
                 return instance.member.get_member_type_display()
        except Membro.DoesNotExist:
            return None
        return 'N/A'
    get_member_type_display_for_admin.short_description = 'Member Type'

class CategoriaAdmin(admin.ModelAdmin):
    list_display = ['nome']
    search_fields = ['nome']

class AutorAdmin(admin.ModelAdmin):
    list_display = ['primeiro_nome', 'sobrenome']
    search_fields = ['primeiro_nome', 'sobrenome']

class EditoraAdmin(admin.ModelAdmin):
    list_display = ['primeiro_nome', 'sobrenome']
    search_fields = ['primeiro_nome', 'sobrenome']

class LivroAdmin(admin.ModelAdmin):
    list_display = ['titulo', 'categoria', 'editora_display', 'disponivel']
    search_fields = ['titulo', 'autores__primeiro_nome', 'autores__sobrenome', 'categoria__nome']
    list_filter = ['categoria', 'disponivel', 'autores']
    filter_horizontal = ('autores',)

    def editora_display(self, obj):
        if obj.editora:
            return f"{obj.editora.primeiro_nome} {obj.editora.sobrenome}"
        return None
    editora_display.short_description = 'Editora'

class EdicaoAdmin(admin.ModelAdmin):
    list_display = ['livro_titulo', 'numero_edicao', 'data_lancamento', 'paginas']
    list_filter = ['data_lancamento', 'livro']
    search_fields = ['livro__titulo']

    def livro_titulo(self, obj):
        return obj.livro.titulo
    livro_titulo.short_description = 'Livro titulo'
    livro_titulo.admin_order_field = 'livro__titulo'

class MembroAdmin(admin.ModelAdmin):
    list_display = ['get_username', 'tipo_membro', 'get_usuario_email']
    search_fields = ['usuario__username', 'usuario__email']
    list_filter = ['tipo_membro']
    list_select_related = ('usuario',)

    def get_username(self, obj):
        return obj.usuario.username
    get_username.short_description = 'Username'
    get_username.admin_order_field = 'usuario__username'

    def get_usuario_email(self, obj):
        return obj.usuario.email
    get_usuario_email.short_description = 'Email'
    get_usuario_email.admin_order_field = 'usuario__email'

# --- Updated EmprestimoAdmin ---
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ['livro_titulo_display', 'edicao_info', 'membro_username', 'data_emprestimo', 'data_devolucao', 'status', 'data_devolucao_real']
    list_filter = ['status', 'membro__tipo_membro', 'data_emprestimo', 'data_devolucao']
    search_fields = ['livro__titulo', 'membro__usuario__username', 'edicao__numero_edicao']
    list_select_related = ('livro', 'edicao', 'membro', 'membro__usuario')
    autocomplete_fields = ['membro', 'livro', 'edicao']

    actions = ['approve_selected_requests', 'reject_selected_requests', 'mark_as_returned_admin']

    def livro_titulo_display(self, obj):
        return obj.livro.titulo
    livro_titulo_display.short_description = 'Livro'
    livro_titulo_display.admin_order_field = 'livro__titulo'

    def edicao_info(self, obj):
        if obj.edition:
            return f"Ed. {obj.edition.edition_number}"
        return "N/A"
    edicao_info.short_description = 'Edicao'

    def membro_username(self, obj):
        return obj.membro.usuario.username
    membro_username.short_description = 'Membro'
    membro_username.admin_order_field = 'membro__usuario__username'

    # --- Custom Actions ---
    def approve_selected_requests(self, request, queryset):
        updated_count = 0
        for req in queryset.filter(status='SOLICITADO'): # Sirf 'SOLICITADO' status wali requests ko approve karein
            if req.livro.is_available: # Check karein ke livro abhi bhi available hai
                req.status = 'EMITIDO' # Status ko 'EMITIDO' set karein
                
                if not req.data_devolucao: # Agar data_devolucao set nahi hai
                    req.data_devolucao = (timezone.now() + timedelta(days=14)).date() # Example: 14 din
                
                req.save() 
                updated_count += 1
            else:
                self.message_user(request, f"Book '{req.livro.titulo}' is no longer available to issue for request by {req.membro.usuario.username}.", level=messages.WARNING)
        
        if updated_count > 0:
            self.message_user(request, f"{updated_count} request(s) successfully approved and marked as ISSUED.")
    approve_selected_requests.short_description = "Approve selected requests (Set to ISSUED)"

    def reject_selected_requests(self, request, queryset):
        
        updated_count = queryset.filter(status='SOLICITADO').update(status='REJEITADO')
        
        if updated_count > 0:
            self.message_user(request, f"{updated_count} request(s) successfully REJECTED.")
    reject_selected_requests.short_description = "Reject selected requests"

    def mark_as_returned_admin(self, request, queryset):
        updated_count = 0
        for req in queryset.filter(status='EMITIDO'): # Sirf 'EMITIDO' status wali books ko returned mark karein
            req.status = 'DEVOLVIDO'
            req.data_devolucao_real = timezone.now().date() # Aaj ki date
            req.save() # Model ka overridden save() method call hoga (book availability update ke liye)
            updated_count += 1
        if updated_count > 0:
            self.message_user(request, f"{updated_count} livro(s) marcados(s) como DEVOLVIDO(S).")
    mark_as_returned_admin.short_description = "Marcar os livros EMPRESTADOS selecionados como DEVOLVIDOS"

# --- Register Models with Admin Site ---
if admin.site.is_registered(AuthUser):
    admin.site.unregister(AuthUser)
admin.site.register(AuthUser, CustomUserAdmin)
admin.site.register(Livro, LivroAdmin)
admin.site.register(Categoria, CategoriaAdmin)
admin.site.register(Autor, AutorAdmin)
admin.site.register(Editora, EditoraAdmin)
admin.site.register(Edicao, EdicaoAdmin)
admin.site.register(Membro, MembroAdmin)
admin.site.register(Emprestimo, EmprestimoAdmin)