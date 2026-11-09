
from django.test import TestCase
from django.urls import reverse


class PaginaInicialTest(TestCase):

    def test_pagina_inicial_carrega(self):
        resposta = self.client.get(reverse('portal:inicio'))

        self.assertEqual(resposta.status_code, 200)
        self.assertTemplateUsed(resposta, 'portal/inicio.html')
        self.assertTemplateUsed(resposta, 'base.html')
