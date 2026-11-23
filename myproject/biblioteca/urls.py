from django.urls import path

from . import views

urlpatterns = [
    path('', views.inicio, name='inicio'),
    path(
        'minha-conta/',
        views.MinhaContaView.as_view(),
        name='minha_conta',
    ),
]