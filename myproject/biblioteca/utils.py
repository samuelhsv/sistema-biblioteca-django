from django.core.exceptions import ObjectDoesNotExist

def obter_membro(request):
    """
    Verifica se o usuário está autenticado e tenta retornar o Membro vinculado.
    Se não houver um membro associado (como no caso de um bibliotecário), 
    retorna None em vez de quebrar a página com Erro 500.
    """
    if request.user.is_authenticated:
        try:
            # Tenta acessar o membro vinculado através do OneToOneField (related_name="membro")
            return request.user.membro
        except ObjectDoesNotExist:
            return None
    return None