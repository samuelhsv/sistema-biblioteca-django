from django.urls import path
from . import views

app_name = "inventario"

urlpatterns = [
    path(
        "conferencia/<int:conferencia_id>/divergencias/",
        views.relatorio_divergencias,
        name="relatorio_divergencias",
    ),
]