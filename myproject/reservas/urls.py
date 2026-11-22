from django.urls import path
from . import views

app_name = "reservas"
urlpatterns = [
    path("solicitar/<int:livro_pk>/", views.solicitar_reserva, name="solicitar"),
    path("<int:pk>/cancelar/", views.cancelar_reserva, name="cancelar"),
]