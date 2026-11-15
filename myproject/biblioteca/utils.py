from django.core.exceptions import ObjectDoesNotExist
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

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

def enviar_email(assunto, template, contexto, destinatario):
    mensagem = render_to_string(template, contexto)

    send_mail(
        subject=assunto,
        message=mensagem,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[destinatario],
    )