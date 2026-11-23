from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings

class Profissional(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profissional',
        null=True,  # temporário, para a migração rodar com dados mocados existentes 
    )
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

    data_nascimento = models.DateField(null=True, blank=True)
    cpf = models.CharField(max_length=14, blank=False)
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
        DUASVEZES = 'DUAS VEZES', 'Duas vezes por semana'
        SEMANAL = 'SEMANAL', 'Semanal'
        QUINZENAL = 'QUINZENAL', 'Quinzenal'
        MENSAL = 'MENSAL', 'Mensal'

    paciente = models.ForeignKey(
        Paciente,
        on_delete=models.PROTECT,
        null = True, # temporario, mudar quando mudar pra postgres
        blank = True,
        related_name='tratamentos'
    )

    data_inicio = models.DateField()
    data_fim_prevista = models.DateField(null=True, blank=True)

    frequencia = models.CharField(
        max_length=12,
        choices=Frequencia.choices
    )

    objetivo = models.TextField(blank=True)

    ativo = models.BooleanField(default=True)

    def __str__(self):
        return f'Tratamento de {self.paciente} desde {self.data_inicio:%d/%m/%Y}'

class Atividade(models.Model):
    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.CASCADE,
        db_column='id_consulta',
        related_name='atividades',
    )
    atividade = models.TextField()

    class Meta:
        db_table = 'atividade'

class ObservacaoConsulta(models.Model):

    class Tipo(models.TextChoices):
        PROBLEMA = 'PROBLEMA', 'Problema relatado'
        EVOLUCAO = 'EVOLUCAO', 'Evolução'
        OUTRO = 'OUTRO', 'Outro'

    consulta = models.ForeignKey(
        Consulta,
        on_delete=models.PROTECT,
        db_column='id_consulta',
        related_name='observacoes'
    )

    tipo = models.CharField(
        max_length=10,
        choices=Tipo.choices,
        default=Tipo.OUTRO
    )

    observacao = models.TextField()

    data_registro = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'observacao_consulta'

class ObjetivoTerapeutico(models.Model):

    class Status(models.TextChoices):
        PENDENTE = 'PENDENTE', 'Pendente'
        ANDAMENTO = 'ANDAMENTO', 'Em andamento'
        CONCLUIDO = 'CONCLUIDO', 'Concluído'

    tratamento = models.ForeignKey(
        Tratamento,
        on_delete=models.PROTECT,
        related_name='objetivos'
    )

    descricao = models.TextField()

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.PENDENTE
    )
    def __str__(self):
        return f'{self.descricao[:50]} ({self.get_status_display()})'

