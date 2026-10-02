import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from agenda.models import Consulta, Paciente, Profissional, Tratamento


class Command(BaseCommand):
    help = 'Cria dados ficticios para testar a AgendaPsi.'

    def add_arguments(self, parser):
        parser.add_argument('--profissionais', type=int, default=25)
        parser.add_argument('--pacientes', type=int, default=250)
        parser.add_argument('--consultas', type=int, default=500)
        parser.add_argument('--tratamentos', type=int, default=300)
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Apaga os dados da agenda antes de criar a carga fake.',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        fake = Faker('pt_BR')

        if options['clear']:
            Tratamento.objects.all().delete()
            Consulta.objects.all().delete()
            Paciente.objects.all().delete()
            Profissional.objects.all().delete()

        profissionais = [
            Profissional(
                nome=fake.name(),
                email=fake.unique.email(),
                telefone=fake.phone_number()[:20],
                crp=f'CRP-{fake.unique.random_number(digits=7, fix_len=True)}',
            )
            for _ in range(options['profissionais'])
        ]
        Profissional.objects.bulk_create(profissionais)

        pacientes = [
            Paciente(
                profissional=random.choice(profissionais),
                nome=fake.name(),
                telefone=fake.phone_number()[:20],
                email=fake.email(),
            )
            for _ in range(options['pacientes'])
        ]
        Paciente.objects.bulk_create(pacientes)

        agora = timezone.now()
        consultas = [
            Consulta(
                paciente=random.choice(pacientes),
                data_hora=agora + timedelta(days=random.randint(-180, 180)),
                status=random.choice([status.value for status in Consulta.Status]),
            )
            for _ in range(options['consultas'])
        ]
        Consulta.objects.bulk_create(consultas)

        tratamentos = []
        for _ in range(options['tratamentos']):
            data_inicio = fake.date_between(start_date='-1y', end_date='today')
            tratamentos.append(
                Tratamento(
                    consulta=random.choice(consultas),
                    data_inicio=data_inicio,
                    data_fim_prevista=data_inicio + timedelta(days=random.randint(30, 365)),
                    frequencia=random.choice([
                        frequencia.value for frequencia in Tratamento.Frequencia
                    ]),
                    ativo=random.choice([True, False]),
                )
            )
        Tratamento.objects.bulk_create(tratamentos)

        self.stdout.write(self.style.SUCCESS(
            f'Carga concluida: {len(profissionais)} profissionais, '
            f'{len(pacientes)} pacientes, {len(consultas)} consultas e '
            f'{len(tratamentos)} tratamentos.'
        ))
