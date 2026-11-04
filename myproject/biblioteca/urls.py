from django.urls import path

from . import views
from django.contrib import admin
from django.urls import path, include
path('contas/', include('django.contrib.auth.urls')),

urlpatterns = [
    # Rota para acessar o painel administrativo do Django
    path('admin/', admin.site.urls),
    
    # Inclui automaticamente as rotas de autenticação do Django (/contas/login/, /contas/logout/, etc.)
    path('contas/', include('django.contrib.auth.urls')), 
    
    # path('', include('portal.urls')), # Suas rotas do portal da biblioteca
]