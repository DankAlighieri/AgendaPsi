from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

class Profissional(models.Model):
    nome = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20)
    crp = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.nome


class Paciente(models.Model):
    profissional = models.ForeignKey(
        Profissional,
        on_delete=models.CASCADE,
        related_name='pacientes'
    )

    nome = models.CharField(max_length=150)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)

    def __str__(self):
        return self.nome

class Agenda(models.Model):
    profissional = models.ForeignKey(
        Profissional, on_delete=models.CASCADE, related_name='agenda'
    )
    data_hora = models.DateTimeField('Data e horário')

    class Meta:
        ordering = ['data_hora']
        constraints = [
            models.UniqueConstraint(
                fields=['profissional', 'data_hora'], name='agenda_horario_unico'
            ),
        ]

    @property
    def ocupado(self):
        # Inclui consultas anteriores à criação da tabela de agenda.
        return Consulta.objects.filter(
            paciente__profissional_id=self.profissional_id,
            data_hora=self.data_hora,
        ).exclude(status=Consulta.Status.CANCELADA).exists()

    def __str__(self):
        horario = timezone.localtime(self.data_hora)
        return f'{horario:%d/%m/%Y %H:%M} - {self.profissional}'


class Consulta(models.Model):

    class Status(models.TextChoices):
        AGENDADA = 'AGENDADA', 'Agendada'
        REALIZADA = 'REALIZADA', 'Realizada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.CASCADE,
        related_name='consultas'
    )

    data_hora = models.DateTimeField()

    agenda = models.ForeignKey(
        Agenda, on_delete=models.PROTECT, related_name='consultas',
        null=True, blank=True,
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AGENDADA
    )

    google_event_id = models.CharField(
        max_length=255,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['agenda'],
                condition=~models.Q(status='CANCELADA'),
                name='consulta_ativa_por_horario',
            ),
        ]

    def clean(self):
        super().clean()
        if self.agenda_id and self.paciente_id:
            if self.agenda.profissional_id != self.paciente.profissional_id:
                raise ValidationError('O paciente deve pertencer ao psicólogo da agenda.')
            if self.data_hora != self.agenda.data_hora:
                raise ValidationError('A consulta deve usar a data e o horário da agenda.')
        if self.paciente_id and self.data_hora and self.status != self.Status.CANCELADA:
            conflito = Consulta.objects.filter(
                paciente__profissional_id=self.paciente.profissional_id,
                data_hora=self.data_hora,
            ).exclude(status=self.Status.CANCELADA).exclude(pk=self.pk)
            if conflito.exists():
                raise ValidationError('Este horário já está ocupado.')

    def save(self, *args, **kwargs):
        self.clean()
        return super().save(*args, **kwargs)

class Tratamento(models.Model):

    class Frequencia(models.TextChoices):
        DUASVEZES = 'DUAS VEZES', 'Duas Vezes'
        SEMANAL = 'SEMANAL', 'Semanal'
        QUINZENAL = 'QUINZENAL', 'Quinzenal'
        MENSAL = 'MENSAL', 'Mensal'

    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.CASCADE,
        related_name='tratamentos'
    )

    data_inicio = models.DateField()
    data_fim_prevista = models.DateField()

    frequencia = models.CharField(
        max_length=10,
        choices=Frequencia.choices
    )

    ativo = models.BooleanField(default=True)
