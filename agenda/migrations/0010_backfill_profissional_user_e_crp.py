import re

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.db import migrations


def criar_usuarios_faltantes(apps, schema_editor):
    """Cria um User, sem senha utilizável, para cada Profissional sem usuário."""
    Profissional = apps.get_model('agenda', 'Profissional')
    User = apps.get_model(*settings.AUTH_USER_MODEL.split('.'))
    db = schema_editor.connection.alias

    for profissional in Profissional.objects.using(db).filter(user__isnull=True):
        email = profissional.email.strip().lower()
        username = email[:150]
        # Um usuário já existente com o mesmo nome não é vinculado automaticamente.
        if User.objects.using(db).filter(username__iexact=username).exists():
            sufixo = f'#{profissional.pk}'
            username = f'{email[:150 - len(sufixo)]}{sufixo}'
        profissional.user = User.objects.using(db).create(
            username=username, email=email, password=make_password(None),
        )
        profissional.save(update_fields=['user'])


def normalizar_crps(apps, schema_editor):
    """Remove a formatação dos CRPs antigos, sem criar duplicidades."""
    Profissional = apps.get_model('agenda', 'Profissional')
    db = schema_editor.connection.alias

    for profissional in Profissional.objects.using(db).all():
        crp = re.sub(r'[\s./-]', '', profissional.crp)
        if crp == profissional.crp:
            continue
        if Profissional.objects.using(db).filter(crp=crp).exists():
            continue
        profissional.crp = crp
        profissional.save(update_fields=['crp'])


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0009_alter_paciente_email_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RunPython(criar_usuarios_faltantes, migrations.RunPython.noop),
        migrations.RunPython(normalizar_crps, migrations.RunPython.noop),
    ]
