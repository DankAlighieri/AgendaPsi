from django.db import models

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


class Tratamento(models.Model):

    class Frequencia(models.TextChoices):
        DUASVEZES = 'DUAS VEZES', 'Duas Vezes'
        SEMANAL = 'SEMANAL', 'Semanal'
        QUINZENAL = 'QUINZENAL', 'Quinzenal'
        MENSAL = 'MENSAL', 'Mensal'

    paciente = models.ForeignKey(
        Paciente,
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


class Consulta(models.Model):

    class Status(models.TextChoices):
        AGENDADA = 'AGENDADA', 'Agendada'
        REALIZADA = 'REALIZADA', 'Realizada'
        CANCELADA = 'CANCELADA', 'Cancelada'

    tratamento = models.ForeignKey(
        Tratamento,
        on_delete=models.CASCADE,
        related_name='consultas'
    )

    data_hora = models.DateTimeField()

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.AGENDADA
    )

    google_event_id = models.CharField(
        max_length=255,
        blank=True
    )