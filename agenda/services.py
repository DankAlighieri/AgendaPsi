from datetime import datetime, timezone as datetime_timezone
from hashlib import sha256
from zoneinfo import ZoneInfo
from django.db import IntegrityError, transaction
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import time, timedelta
from .models import Agenda, Consulta, LoteAgenda


HORAS_ATENDIMENTO = (8, 9, 10, 11, 14, 15, 16, 17)
DIAS_DISPONIVEIS = 30
MAX_SEMANAS_LOTE = 52




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


def _data_hora_local(data, hora):
    zona = ZoneInfo('America/Sao_Paulo')
    data_hora_sem_fuso = datetime.combine(data, hora)
    candidatos = []

    for fold in (0, 1):
        candidato = data_hora_sem_fuso.replace(tzinfo=zona, fold=fold)
        volta = (
            candidato
            .astimezone(datetime_timezone.utc)
            .astimezone(zona)
            .replace(tzinfo=None)
        )
        if volta == data_hora_sem_fuso:
            candidatos.append(candidato)

    if not candidatos:
        raise ValidationError(
            'Essa hora local não existe por causa da mudança de fuso.'
        )

    offsets = {candidato.utcoffset() for candidato in candidatos}
    if len(offsets) > 1:
        raise ValidationError(
            'Essa hora local é ambígua por causa da mudança de fuso.'
        )

    return candidatos[0]


def criar_horario_individual(*, profissional, data, hora):
    data_hora = _data_hora_local(data, hora)

    if data_hora <= timezone.now():
        raise ValidationError('Selecione uma data e horário futuros.')
    if not horario_de_atendimento(data_hora):
        raise ValidationError(
            'Selecione um horário de segunda a sexta, das 8h às 12h ou das 14h às 18h.'
        )

    try:
        with transaction.atomic():
            return Agenda.objects.create(
                profissional=profissional,
                data_hora=data_hora,
            )
    except IntegrityError as exc:
        existe = Agenda.objects.filter(
            profissional=profissional,
            data_hora=data_hora,
        ).exists()

        if existe:
            raise ValidationError(
                'Este horário já está cadastrado na agenda.'
            ) from exc

        raise


def _mensagem_conflitos(conflitos):
    datas = ', '.join(
        timezone.localtime(data_hora).strftime('%d/%m/%Y %H:%M')
        for data_hora in conflitos
    )
    return f'Nenhum horário foi cadastrado. Conflitos: {datas}.'


def criar_horarios_lote(
    *,
    profissional,
    data_inicio,
    dia_semana,
    hora,
    semanas,
    chave_idempotencia,
):
    if (
        not isinstance(semanas, int)
        or isinstance(semanas, bool)
        or not 1 <= semanas <= MAX_SEMANAS_LOTE
    ):
        raise ValidationError(
            f'A quantidade de semanas deve estar entre 1 e {MAX_SEMANAS_LOTE}.'
        )

    primeiro_dia = data_inicio + timedelta(
        days=(dia_semana - data_inicio.weekday()) % 7
    )

    horarios = [
        _data_hora_local(
            primeiro_dia + timedelta(weeks=semana),
            hora,
        )
        for semana in range(semanas)
    ]

    if any(not horario_de_atendimento(data_hora) for data_hora in horarios):
        raise ValidationError(
            'Selecione um horário de segunda a sexta, das 8h às 12h ou das 14h às 18h.'
        )

    if any(data_hora <= timezone.now() for data_hora in horarios):
        raise ValidationError('Todos os horários do lote devem ser futuros.')

    payload = '|'.join(data_hora.isoformat() for data_hora in horarios)
    payload_hash = sha256(payload.encode()).hexdigest()

    try:
        with transaction.atomic():
            lote_anterior = LoteAgenda.objects.filter(
                profissional=profissional,
                chave_idempotencia=chave_idempotencia,
            ).first()

            if lote_anterior:
                if lote_anterior.payload_hash != payload_hash:
                    raise ValidationError(
                        'Esta chave já foi usada com outros dados.'
                    )
                return 0

            conflitos = list(
                Agenda.objects.filter(
                    profissional=profissional,
                    data_hora__in=horarios,
                )
                .order_by('data_hora')
                .values_list('data_hora', flat=True)
            )

            if conflitos:
                raise ValidationError(_mensagem_conflitos(conflitos))

            LoteAgenda.objects.create(
                profissional=profissional,
                chave_idempotencia=chave_idempotencia,
                payload_hash=payload_hash,
            )

            Agenda.objects.bulk_create([
                Agenda(
                    profissional=profissional,
                    data_hora=data_hora,
                )
                for data_hora in horarios
            ])

    except IntegrityError as exc:
        lote_anterior = LoteAgenda.objects.filter(
            profissional=profissional,
            chave_idempotencia=chave_idempotencia,
        ).first()

        if lote_anterior:
            if lote_anterior.payload_hash == payload_hash:
                return 0
            raise ValidationError(
                'Esta chave já foi usada com outros dados.'
            ) from exc

        conflitos = list(
            Agenda.objects.filter(
                profissional=profissional,
                data_hora__in=horarios,
            )
            .order_by('data_hora')
            .values_list('data_hora', flat=True)
        )

        if conflitos:
            raise ValidationError(_mensagem_conflitos(conflitos)) from exc

        raise

    return len(horarios)
