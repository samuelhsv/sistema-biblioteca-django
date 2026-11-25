from django.urls import path
from . import views
from .views import RenovarEmprestimoView

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path(
        "emprestimos/<int:pk>/renovar/",
        RenovarEmprestimoView.as_view(),
        name="renovar_emprestimo",
    ),
]