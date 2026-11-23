from datetime import datetime, timedelta
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ConsultaForm
from .models import Agenda, Consulta, Paciente, Profissional
from .services import agendar_consulta, horarios_padrao


class AgendamentoTests(TestCase):
    def setUp(self):
        relogio = patch('django.utils.timezone.now', return_value=timezone.make_aware(
            datetime(2026, 10, 26, 7)
        ))
        relogio.start()
        self.addCleanup(relogio.stop)
        self.profissional = Profissional.objects.create(
            nome='Ana', email='ana@example.com', telefone='111', crp='123'
        )
        self.outro = Profissional.objects.create(
            nome='Bruno', email='bruno@example.com', telefone='222', crp='456'
        )
        self.paciente = Paciente.objects.create(
            profissional=self.profissional, nome='Cliente', telefone='333'
        )
        self.outro_paciente = Paciente.objects.create(
            profissional=self.outro, nome='Outro cliente', telefone='444'
        )
        self.horario = Agenda.objects.create(
            profissional=self.profissional,
            data_hora=timezone.localtime(timezone.now() + timedelta(days=1)).replace(
                hour=8, minute=0, second=0, microsecond=0
            ),
        )
        self.url = reverse('cadastroConsulta', args=[self.profissional.pk])

    def reservar(self):
        return agendar_consulta(
            profissional=self.profissional, paciente=self.paciente, horario=self.horario
        )

    def test_formulario_lista_apenas_clientes_e_horarios_livres_do_profissional(self):
        passado = Agenda.objects.create(
            profissional=self.profissional, data_hora=timezone.now() - timedelta(days=1)
        )
        externo = Agenda.objects.create(
            profissional=self.outro, data_hora=self.horario.data_hora
        )
        form = ConsultaForm(profissional=self.profissional)
        self.assertQuerySetEqual(form.fields['paciente'].queryset, [self.paciente])
        self.assertIn(self.horario, form.fields['agenda'].queryset)
        self.assertTrue(all(
            horario.profissional_id == self.profissional.pk
            for horario in form.fields['agenda'].queryset
        ))
        self.assertNotIn(passado, form.fields['agenda'].queryset)
        self.assertNotIn(externo, form.fields['agenda'].queryset)

    def test_post_reserva_e_remove_horario_do_formulario(self):
        response = self.client.post(self.url, {
            'paciente': self.paciente.pk, 'agenda': self.horario.pk,
        })
        self.assertRedirects(response, reverse('agendaProfissional', args=[self.profissional.pk]))
        consulta = Consulta.objects.get()
        self.assertEqual(consulta.agenda, self.horario)
        self.assertEqual(consulta.data_hora, self.horario.data_hora)
        self.assertEqual(consulta.google_event_id, '')
        self.assertTrue(self.horario.ocupado)
        form = ConsultaForm(profissional=self.profissional)
        self.assertNotIn(self.horario, form.fields['agenda'].queryset)
        self.assertContains(self.client.get(reverse('agendaProfissional', args=[self.profissional.pk])), 'Ocupado')

    def test_post_repetido_nao_duplica_consulta(self):
        self.reservar()
        response = self.client.post(self.url, {
            'paciente': self.paciente.pk, 'agenda': self.horario.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Consulta.objects.count(), 1)
        self.assertContains(response, 'Este horário não está disponível')

    def test_formulario_rejeita_cliente_de_outro_profissional(self):
        response = self.client.post(self.url, {
            'paciente': self.outro_paciente.pk, 'agenda': self.horario.pk,
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Consulta.objects.exists())

    def test_servico_rejeita_horario_de_outro_profissional(self):
        with self.assertRaises(ValidationError):
            agendar_consulta(profissional=self.outro, paciente=self.outro_paciente, horario=self.horario)

    def test_formulario_rejeita_horario_de_outro_profissional(self):
        externo = Agenda.objects.create(profissional=self.outro, data_hora=self.horario.data_hora)
        response = self.client.post(self.url, {'paciente': self.paciente.pk, 'agenda': externo.pk})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Consulta.objects.exists())

    def test_reserva_revalida_horario_apos_formulario_ser_validado(self):
        form = ConsultaForm(
            {'paciente': self.paciente.pk, 'agenda': self.horario.pk},
            profissional=self.profissional,
        )
        self.assertTrue(form.is_valid())
        self.reservar()
        with self.assertRaises(ValidationError):
            agendar_consulta(
                profissional=self.profissional, paciente=form.cleaned_data['paciente'],
                horario=form.cleaned_data['agenda'],
            )
        self.assertEqual(Consulta.objects.count(), 1)

    def test_profissionais_podem_atender_no_mesmo_horario(self):
        self.reservar()
        externo = Agenda.objects.create(profissional=self.outro, data_hora=self.horario.data_hora)
        agendar_consulta(profissional=self.outro, paciente=self.outro_paciente, horario=externo)
        self.assertTrue(externo.ocupado)
        self.assertEqual(Consulta.objects.count(), 2)

    def test_servico_rejeita_horario_passado(self):
        self.horario.data_hora = timezone.now() - timedelta(days=1)
        self.horario.save()
        with self.assertRaises(ValidationError):
            self.reservar()

    def test_cancelamento_libera_horario(self):
        consulta = self.reservar()
        consulta.status = Consulta.Status.CANCELADA
        consulta.save()
        self.assertFalse(self.horario.ocupado)
        self.reservar()
        self.assertEqual(Consulta.objects.count(), 2)

    def test_consulta_legada_tambem_bloqueia_horario(self):
        Consulta.objects.create(paciente=self.paciente, data_hora=self.horario.data_hora)
        form = ConsultaForm(profissional=self.profissional)
        self.assertNotIn(self.horario, form.fields['agenda'].queryset)
        with self.assertRaises(ValidationError):
            self.reservar()

    def test_banco_impede_duas_consultas_ativas_no_mesmo_horario(self):
        self.reservar()
        with self.assertRaises(IntegrityError), transaction.atomic():
            Consulta.objects.bulk_create([
                Consulta(paciente=self.paciente, agenda=self.horario, data_hora=self.horario.data_hora)
            ])

    def test_modelo_rejeita_inconsistencia_entre_cliente_e_agenda(self):
        with self.assertRaises(ValidationError):
            Consulta.objects.create(
                paciente=self.outro_paciente, agenda=self.horario,
                data_hora=self.horario.data_hora,
            )

    def test_banco_impede_horario_duplicado_por_profissional(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Agenda.objects.create(profissional=self.profissional, data_hora=self.horario.data_hora)

    def test_horarios_sao_gerados_sem_cadastro_manual_e_sem_duplicar(self):
        response = self.client.get(reverse('agendaProfissional', args=[self.outro.pk]))
        self.assertEqual(response.status_code, 200)
        quantidade = self.outro.agenda.count()
        self.assertGreater(quantidade, 0)
        self.client.get(reverse('agendaProfissional', args=[self.outro.pk]))
        self.assertEqual(self.outro.agenda.count(), quantidade)
        self.assertNotContains(response, 'Adicionar horário')

    def test_grade_respeita_dias_intervalos_e_limite_de_trinta_dias(self):
        horarios = list(horarios_padrao(self.profissional))
        for horario in horarios:
            local = timezone.localtime(horario.data_hora)
            self.assertLess(local.weekday(), 5)
            self.assertIn(local.hour, (8, 9, 10, 11, 14, 15, 16, 17))
            self.assertEqual((local.minute, local.second, local.microsecond), (0, 0, 0))
            self.assertGreater(horario.data_hora, timezone.now())
            self.assertLess(local.date(), timezone.localdate() + timedelta(days=30))
        hoje = [timezone.localtime(h.data_hora).hour for h in horarios if timezone.localdate(h.data_hora) == timezone.localdate()]
        self.assertEqual(hoje, [8, 9, 10, 11, 14, 15, 16, 17])

    def test_horarios_passados_de_hoje_nao_aparecem(self):
        with patch('django.utils.timezone.now', return_value=timezone.make_aware(datetime(2026, 10, 26, 10, 30))):
            horarios = horarios_padrao(self.profissional)
            hoje = [timezone.localtime(h.data_hora).hour for h in horarios if timezone.localdate(h.data_hora) == timezone.localdate()]
            self.assertEqual(hoje, [11, 14, 15, 16, 17])

    def test_formulario_e_servico_rejeitam_horarios_fora_do_expediente(self):
        for data in [datetime(2026, 10, 27, 12), datetime(2026, 10, 27, 13),
                     datetime(2026, 10, 27, 18), datetime(2026, 10, 27, 8, 30),
                     datetime(2026, 10, 31, 8), datetime(2026, 11, 1, 8)]:
            with self.subTest(data=data):
                horario = Agenda.objects.create(profissional=self.profissional, data_hora=timezone.make_aware(data))
                form = ConsultaForm(
                    {'paciente': self.paciente.pk, 'agenda': horario.pk}, profissional=self.profissional,
                )
                self.assertFalse(form.is_valid())
                with self.assertRaises(ValidationError):
                    agendar_consulta(profissional=self.profissional, paciente=self.paciente, horario=horario)

    def test_paginas_e_profissional_inexistente(self):
        self.assertContains(self.client.get(reverse('index')), 'Ana')
        self.assertContains(self.client.get(self.url), 'Cadastrar consulta')
        self.assertEqual(self.client.get(reverse('agendaProfissional', args=[99999])).status_code, 404)
