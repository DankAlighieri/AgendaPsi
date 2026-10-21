from datetime import datetime, time, timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Agenda, Consulta


HORAS_ATENDIMENTO = (8, 9, 10, 11, 14, 15, 16, 17)
DIAS_DISPONIVEIS = 30


def horario_de_atendimento(data_hora):
    local = timezone.localtime(data_hora)
    return (
        local.weekday() < 5 and local.hour in HORAS_ATENDIMENTO
        and local.minute == local.second == local.microsecond == 0
    )


def horarios_padrao(profissional):
    """Disponibiliza os próximos 30 dias sem cadastro manual de horários."""
    agora = timezone.now()
    hoje = timezone.localdate(agora)
    datas = []
    for deslocamento in range(DIAS_DISPONIVEIS):
        dia = hoje + timedelta(days=deslocamento)
        if dia.weekday() >= 5:
            continue
        for hora in HORAS_ATENDIMENTO:
            inicio = timezone.make_aware(datetime.combine(dia, time(hour=hora)))
            if inicio > agora:
                datas.append(inicio)
    existentes = set(Agenda.objects.filter(
        profissional=profissional, data_hora__in=datas
    ).values_list('data_hora', flat=True))
    Agenda.objects.bulk_create([
        Agenda(profissional=profissional, data_hora=inicio)
        for inicio in datas if inicio not in existentes
    ], ignore_conflicts=True)
    return Agenda.objects.filter(profissional=profissional, data_hora__in=datas)


def agendar_consulta(*, profissional, paciente, horario):
    """Reserva o horário localmente. A integração com Google Agenda é futura."""
    try:
        with transaction.atomic():
            horario = Agenda.objects.select_for_update().get(
                pk=horario.pk, profissional=profissional
            )
            if paciente.profissional_id != profissional.pk:
                raise ValidationError('Selecione um cliente deste psicólogo.')
            if horario.data_hora <= timezone.now():
                raise ValidationError('Selecione um horário no futuro.')
            if not horario_de_atendimento(horario.data_hora):
                raise ValidationError('Selecione um horário de segunda a sexta, das 8h às 12h ou das 14h às 18h.')
            consulta = Consulta(
                paciente=paciente, agenda=horario, data_hora=horario.data_hora
            )
            # A restrição no banco também impede reservas simultâneas.
            consulta.save()
            return consulta
    except Agenda.DoesNotExist as exc:
        raise ValidationError('Horário indisponível para este psicólogo.') from exc
    except IntegrityError as exc:
        raise ValidationError('Este horário já está ocupado. Selecione outro horário.') from exc
