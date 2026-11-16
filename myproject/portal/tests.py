
from django.test import TestCase
from django.urls import reverse
from biblioteca.models import Categoria, Livro


class PaginaInicialTest(TestCase):

    def test_pagina_inicial_carrega(self):
        resposta = self.client.get(reverse('portal:inicio'))

        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'portal/inicio.html')
        self.assertTemplateUsed(resposta, 'base.html')


class CatalogoTest(TestCase):

    def test_catalogo_carrega(self):
        resposta = self.client.get(reverse('portal:catalogo'))

        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'portal/catalogo.html')

    def test_busca_por_titulo(self):
        categoria = Categoria.objects.create(
            nome='Produtividade/Gestão de Tempo'
        )

        Livro.objects.create(
            titulo='Essencialismo',
            categoria=categoria
        )

        resposta = self.client.get(
            reverse('portal:catalogo'),
            {'q': 'Essencialismo'}
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, 'Essencialismo')

    def test_busca_sem_resultados(self):
        resposta = self.client.get(
            reverse('portal:catalogo'),
            {'q': 'LivroQueNaoExiste'}
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.context['livros'].count(), 0)
