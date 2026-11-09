
from django.shortcuts import render
from biblioteca.models import Livro, Categoria


def inicio(request):
    total_titulos = Livro.objects.count()

    total_disponiveis = sum(
        Livro.objects.values_list('qtd_disponivel', flat=True)
    )

    total_categorias = Categoria.objects.count()

    livros_recentes = Livro.objects.select_related(
        'categoria'
    ).prefetch_related(
        'autores'
    ).order_by(
        '-qtd_disponivel', '-id'
    )[:6]

    return render(request, 'portal/inicio.html', {
        'total_titulos': total_titulos,
        'total_disponiveis': total_disponiveis,
        'total_categorias': total_categorias,
        'livros_recentes': livros_recentes
    })


def catalogo(request):
    busca = request.GET.get('q', '')

    livros = Livro.objects.select_related(
        'categoria'
    ).prefetch_related(
        'autores'
    ).filter(
        titulo__icontains=busca
    ).order_by('titulo')

    return render(request, 'portal/catalogo.html', {
        'livros': livros,
        'busca': busca
    })
