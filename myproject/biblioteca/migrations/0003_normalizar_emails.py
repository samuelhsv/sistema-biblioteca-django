from collections import Counter

from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import migrations


def normalizar_emails(apps, schema_editor):
    # Usa o modelo histórico da migração, não o models.py atual.
    Membro = apps.get_model("biblioteca", "Membro")
    banco = schema_editor.connection.alias

    registros = list(
        Membro.objects.using(banco).values_list("pk", "email")
    )

    normalizados = []
    invalidos = 0

    for pk, email in registros:
        email_normalizado = (email or "").strip().lower() or None

        if email_normalizado:
            try:
                validate_email(email_normalizado)
            except ValidationError:
                invalidos += 1

        normalizados.append((pk, email_normalizado))

    contagem = Counter(
        email
        for _, email in normalizados
        if email is not None
    )

    grupos_duplicados = sum(
        1
        for quantidade in contagem.values()
        if quantidade > 1
    )

    # Confere todos os registros antes de alterar qualquer um.
    # Não exclui membros nem escolhe automaticamente qual e-mail manter.
    if invalidos or grupos_duplicados:
        raise RuntimeError(
            "Normalização interrompida. "
            f"E-mails com formato inválido: {invalidos}. "
            f"Grupos de e-mails duplicados: {grupos_duplicados}. "
            "Revise os cadastros antes de executar novamente."
        )

    for pk, email in normalizados:
        Membro.objects.using(banco).filter(pk=pk).update(
            email=email
        )


class Migration(migrations.Migration):
    dependencies = [
        ("biblioteca", "0002_curso_membro_periodo_membro_curso"),
    ]

    operations = [
        migrations.RunPython(
            normalizar_emails,
            reverse_code=migrations.RunPython.noop,
        ),
    ]