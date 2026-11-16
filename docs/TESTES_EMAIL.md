# Testes de envio de e-mail

## 1. Testes automatizados

Os testes automatizados verificam o funcionamento da função `enviar_email` utilizando o backend de memória do Django (`mail.outbox`).

Para executar:

```bash
python manage.py test biblioteca.tests.EmailTests
```

Os testes verificam:
- Se o e-mail foi adicionado à fila de envio.
- Se o destinatário está correto.
- Se o assunto foi definido corretamente.
- Se o conteúdo do template está presente no corpo da mensagem.

## 2. Teste manual local

O ambiente local utiliza o backend de console do Django.

No terminal, execute:

```bash
python manage.py shell
```

Depois:

```python
from biblioteca.utils import enviar_email

enviar_email(
    "Teste Biblioteca FLUI",
    "emails/teste.txt",
    {"nome": "Usuário de teste"},
    "email@exemplo.com"
)
```

O conteúdo da mensagem deverá aparecer no terminal. Nesse ambiente, o e-mail não é enviado para a caixa postal.

**Observação sobre a saída no terminal:** É normal que o conteúdo do e-mail apareça com alguns caracteres codificados no formato MIME (Quoted-Printable), especialmente letras acentuadas e caracteres especiais. Por exemplo, `Ol=C3=A1, Usu=C3=A1rio de teste!` representa `Olá, Usuário de teste!`. Essa representação faz parte da codificação utilizada na transmissão de mensagens de e-mail e não significa que o template esteja com problemas.

## 3. Teste manual na homologação

No servidor, execute:

```bash
python manage.py sendtestemail seu-email@exemplo.com
```

Verifique a caixa de entrada e a pasta de spam.

Esse comando verifica a configuração de envio do Django. Ele não testa diretamente o template nem a função `enviar_email`.

## 4. Segurança

- Não adicionar a senha de aplicativo ao repositório.
- Manter as credenciais no `.env` do servidor.
- Utilizar valores fictícios no `.env.example`.