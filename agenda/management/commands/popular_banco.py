import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from faker import Faker

from agenda.models import Consulta, Paciente, Profissional, Tratamento


class Command(BaseCommand):
    help = 'Cria dados ficticios para profissionais, pacientes, consultas e tratamentos.'

    def add_arguments(self, parser):
        parser.add_argument('--profissionais', type=int, default=5)
        parser.add_argument('--pacientes-por-profissional', type=int, default=4)
        parser.add_argument('--consultas-por-paciente', type=int, default=2)
        parser.add_argument('--tratamentos-por-consulta', type=int, default=1)
        parser.add_argument('--seed', type=int, default=None)

    @transaction.atomic
    def handle(self, *args, **options):
        seed = options['seed']
        if seed is not None:
            Faker.seed(seed)
            random.seed(seed)

        fake = Faker('pt_BR')
        generator = random.Random(seed)

        professionals_created = 0
        patients_created = 0
        appointments_created = 0
        treatments_created = 0

        for _ in range(options['profissionais']):
            professional = Profissional.objects.create(
                nome=fake.name(),
                email=fake.unique.email(),
                telefone=fake.numerify('(##) #####-####'),
                crp=fake.unique.numerify('##/#####'),
            )
            professionals_created += 1

            for _ in range(options['pacientes_por_profissional']):
                patient = Paciente.objects.create(
                    profissional=professional,
                    nome=fake.name(),
                    telefone=fake.numerify('(##) #####-####'),
                    email=fake.email(),
                )
                patients_created += 1

                for _ in range(options['consultas_por_paciente']):
                    appointment_date = fake.date_time_between(
                        start_date='-1y',
                        end_date='+30d',
                        tzinfo=timezone.get_current_timezone(),
                    )
                    appointment = Consulta.objects.create(
                        paciente=patient,
                        data_hora=appointment_date,
                        status=generator.choice(Consulta.Status.values),
                    )
                    appointments_created += 1

                    for _ in range(options['tratamentos_por_consulta']):
                        start_date = appointment_date.date()
                        Tratamento.objects.create(
                            consulta=appointment,
                            data_inicio=start_date,
                            data_fim_prevista=start_date + timedelta(days=90),
                            frequencia=generator.choice(Tratamento.Frequencia.values),
                            ativo=True,
                        )
                        treatments_created += 1

        self.stdout.write(self.style.SUCCESS(
            'Dados criados com sucesso: '
            f'{professionals_created} profissionais, '
            f'{patients_created} pacientes, '
            f'{appointments_created} consultas e '
            f'{treatments_created} tratamentos.'
        ))