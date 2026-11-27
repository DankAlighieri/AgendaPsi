"""Apoio aos comandos de carga (o prefixo "_" impede que vire um comando)."""
import random
from uuid import uuid4

from django.contrib.auth import get_user_model

from agenda.models import Profissional


def telefone_fake(fake):
    return fake.numerify('(##) 9####-####')


def crp_fake():
    """CRP no formato aceito pelo cadastro: região e registro, só dígitos."""
    while True:
        crp = f'{random.randint(1, 24):02}{random.randint(0, 999999):06}'
        if not Profissional.objects.filter(crp=crp).exists():
            return crp


def criar_profissional(fake, senha=None):
    """Cria o User e o Profissional. Sem senha, o login fica desabilitado."""
    email = f'{fake.user_name()}.{uuid4().hex[:8]}@example.com'
    user = get_user_model().objects.create_user(
        username=email, email=email, password=senha,
    )
    return Profissional.objects.create(
        user=user,
        nome=fake.name(),
        email=email,
        telefone=telefone_fake(fake),
        crp=crp_fake(),
    )
