from datetime import datetime, time, timedelta
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .forms import ConsultaForm, HorariosLoteForm
from .models import Agenda, Consulta, Paciente, Profissional
from .services import (
    MAX_SEMANAS_LOTE,
    agendar_consulta,
    criar_horario_individual,
    criar_horarios_lote,
    horarios_padrao,
)
from .models import Profissional, Paciente
from .forms import ConsultaForm,PacienteFormCadastro, ProfissionalFormCadastro, ProfissionalFormUpdate
from .models import Agenda, Consulta, Paciente, Profissional
from .services import agendar_consulta, horarios_padrao
from agenda.models import Paciente
from agenda.views import cadastroPaciente

from django.contrib.auth import get_user_model



class CadastroPacienteViewTest(TestCase):

    def setUp(self):
        User = get_user_model()

        self.user = User.objects.create_user(#forcando a criação de um usuário para o teste
            username="teste",
            password="123456"
        )

        self.profissional = Profissional.objects.create(
            user=self.user,
            nome="Profissional Teste",
            email="profissional@email.com",
            telefone="87999999999",
            crp="123456"
        )

        self.client.force_login(self.user)#forcando o login do usuário  

    def test_acessar_pagina_cadastro(self):
        response = self.client.get(
            reverse("cadastroPaciente")
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "cadastro.html")

    def test_acesso_sem_login_redireciona_para_login(self):
        self.client.logout()

        response = self.client.get(reverse("cadastroPaciente"))

        self.assertRedirects(
            response,
            f"{reverse('login')}?next={reverse('cadastroPaciente')}",
        )

    def test_cadastrar_paciente_com_dados_validos(self):
        dados = {
            "nome": "Paciente Teste",
            "cpf": "52998224725",
            "telefone": "87988888888",
            "email": "paciente@email.com",
            "data_nascimento": "2000-05-10"
        }

        response = self.client.post(
            reverse("cadastroPaciente"),
            dados
        )

        self.assertRedirects(response, reverse("cadastroPaciente"))

        paciente = Paciente.objects.get(
            cpf="52998224725"
        )

        self.assertEqual(paciente.nome, "Paciente Teste")
        self.assertEqual(
            paciente.profissional,
            self.profissional
        )

    def test_outro_profissional_pode_cadastrar_paciente_com_email_existente(self):
        Paciente.objects.create(
            profissional=self.profissional,
            data_nascimento="2000-05-10",
            cpf="52998224725",
            nome="Paciente Existente",
            telefone="87988888888",
            email="paciente@email.com",
        )
        User = get_user_model()
        outro_user = User.objects.create_user(username="outro")
        outro_profissional = Profissional.objects.create(
            user=outro_user,
            nome="Outro Profissional",
            email="outro-profissional@email.com",
            telefone="87999999998",
            crp="654321",
        )
        self.client.force_login(outro_user)

        response = self.client.post(
            reverse("cadastroPaciente"),
            {
                "nome": "Outro Paciente",
                "cpf": "11144477735",
                "telefone": "87988888887",
                "email": "paciente@email.com",
                "data_nascimento": "2000-05-10",
            },
        )

        self.assertRedirects(response, reverse("cadastroPaciente"))
        paciente = Paciente.objects.get(cpf="11144477735")
        self.assertEqual(paciente.profissional, outro_profissional)

    def test_nao_cadastrar_paciente_com_dados_invalidos(self):
        dados = {
            "nome": "",
            "cpf": "52998224725",
            "telefone": "87988888888",
            "email": "paciente@email.com",
            "data_nascimento": "2000-05-10"
        }

        response = self.client.post(
            reverse("cadastroPaciente"),
            dados
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Paciente.objects.count(), 0)
        self.assertIn("nome", response.context["form"].errors)

    def test_campos_invalidos_exibem_erros_especificos(self):
        dados = {
            "nome": "Paciente Teste",
            "cpf": "52998224725",
            "telefone": "87988888888",
            "email": "email-invalido",
            "data_nascimento": "data-invalida",
        }

        response = self.client.post(reverse("cadastroPaciente"), dados)

        self.assertEqual(response.status_code, 200)
        self.assertIn("email", response.context["form"].errors)
        self.assertIn("data_nascimento", response.context["form"].errors)
        self.assertEqual(Paciente.objects.count(), 0)

    def test_cpf_com_digitos_verificadores_invalidos_nao_cadastra(self):
        dados = {
            "nome": "Paciente Teste",
            "cpf": "529.982.247-24",
            "telefone": "87988888888",
            "email": "paciente@email.com",
            "data_nascimento": "2000-05-10",
        }

        response = self.client.post(reverse("cadastroPaciente"), dados)

        self.assertEqual(response.status_code, 200)
        self.assertIn("cpf", response.context["form"].errors)
        self.assertEqual(Paciente.objects.count(), 0)

    def test_valid_form(self):
        dados = {
            "nome": "João",
            "cpf": "529.982.247-25",
            "telefone": "(87)9 9999-9999",
            "email": "joao@email.com",
            "data_nascimento": "2000-05-10"
        }

        form = PacienteFormCadastro(data=dados)
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["cpf"], "52998224725")

    def test_cpf_com_digitos_repetidos_e_invalido(self):
        dados = {
            "nome": "João",
            "cpf": "111.111.111-11",
            "telefone": "(87)9 9999-9999",
            "email": "joao@email.com",
            "data_nascimento": "2000-05-10",
        }

        form = PacienteFormCadastro(data=dados)

        self.assertFalse(form.is_valid())
        self.assertIn("cpf", form.errors)

    
            

    
    

class AgendamentoTests(TestCase):
    def setUp(self):
        relogio = patch('django.utils.timezone.now', return_value=timezone.make_aware(
            datetime(2026, 10, 26, 7)
        ))
        relogio.start()
        self.addCleanup(relogio.stop)
        self.user = get_user_model().objects.create_user(
            username='ana'
        )
        self.profissional = Profissional.objects.create(
            user=self.user, nome='Ana', email='ana@example.com', telefone='111', crp='123'
        )
        outro_user = get_user_model().objects.create_user(
            username='bruno'
        )
        self.outro = Profissional.objects.create(
            user=outro_user, nome='Bruno', email='bruno@example.com', telefone='222', crp='456'
        )
        self.client.force_login(self.user)
        self.paciente = Paciente.objects.create(
            profissional=self.profissional, nome='Cliente', telefone='333',
            email='cliente@example.com',
        )
        self.outro_paciente = Paciente.objects.create(
            profissional=self.outro, nome='Outro cliente', telefone='444',
            email='outro-cliente@example.com',
        )
        self.horario = Agenda.objects.create(
            profissional=self.profissional,
            data_hora=timezone.localtime(timezone.now() + timedelta(days=1)).replace(
                hour=8, minute=0, second=0, microsecond=0
            ),
        )
        self.url = reverse('cadastroConsulta')

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
        self.assertRedirects(response, reverse('agendaProfissional'))
        consulta = Consulta.objects.get()
        self.assertEqual(consulta.agenda, self.horario)
        self.assertEqual(consulta.data_hora, self.horario.data_hora)
        self.assertEqual(consulta.google_event_id, '')
        self.assertTrue(self.horario.ocupado)
        form = ConsultaForm(profissional=self.profissional)
        self.assertNotIn(self.horario, form.fields['agenda'].queryset)
        self.assertContains(self.client.get(reverse('agendaProfissional')), 'Ocupado')

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
        self.client.force_login(self.outro.user)
        response = self.client.get(reverse('agendaProfissional'))
        self.assertEqual(response.status_code, 200)
        quantidade = self.outro.agenda.count()
        self.assertGreater(quantidade, 0)
        self.client.get(reverse('agendaProfissional'))
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

    def test_horario_manual_fora_da_grade_pode_ser_agendado(self):
        for data in [datetime(2026, 10, 27, 12), datetime(2026, 10, 27, 13),
                     datetime(2026, 10, 27, 18), datetime(2026, 10, 27, 8, 30),
                     datetime(2026, 10, 31, 8), datetime(2026, 11, 1, 8)]:
            with self.subTest(data=data):
                horario = Agenda.objects.create(profissional=self.profissional, data_hora=timezone.make_aware(data))
                form = ConsultaForm(
                    {'paciente': self.paciente.pk, 'agenda': horario.pk}, profissional=self.profissional,
                )
                self.assertTrue(form.is_valid(), form.errors)
                agendar_consulta(profissional=self.profissional, paciente=self.paciente, horario=horario)

    def test_paginas_do_profissional_autenticado(self):
        self.assertContains(self.client.get(reverse('index')), 'Ana')
        self.assertContains(self.client.get(self.url), 'Cadastrar consulta')
        self.assertEqual(self.client.get(reverse('agendaProfissional')).status_code, 200)

    def test_logout_encerra_a_sessao(self):
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_logout_por_get_nao_e_permitido(self):
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertIn('_auth_user_id', self.client.session)

    def test_menu_exibe_botao_de_sair(self):
        self.assertContains(
            self.client.get(reverse('agendaProfissional')),
            f'action="{reverse("logout")}"',
        )

    def test_formulario_limita_semanas_do_lote(self):
        dados = {
            'data_inicio': '2026-10-27',
            'dia_semana': '1',
            'hora': '08:00',
            'semanas': MAX_SEMANAS_LOTE + 1,
            'chave_idempotencia': '9c43d2c8-fcb8-4ed1-af6b-4495e1d239ca',
        }
        form = HorariosLoteForm(data=dados)
        self.assertFalse(form.is_valid())
        self.assertIn('semanas', form.errors)

    def test_servico_rejeita_lote_com_semanas_acima_do_limite(self):
        with self.assertRaises(ValidationError):
            criar_horarios_lote(
                profissional=self.profissional,
                data_inicio=timezone.localdate(),
                dia_semana=0,
                hora=datetime.min.time(),
                semanas=MAX_SEMANAS_LOTE + 1,
                chave_idempotencia='9c43d2c8-fcb8-4ed1-af6b-4495e1d239ca',
            )

    def lote(self, hora=time(14), semanas=8, chave=None):
        return criar_horarios_lote(
            profissional=self.profissional,
            data_inicio=timezone.localdate(),
            dia_semana=1,
            hora=hora,
            semanas=semanas,
            chave_idempotencia=chave or uuid4(),
        )

    def test_lote_assume_horarios_gerados_pela_grade(self):
        horarios_padrao(self.profissional)
        self.assertEqual(self.lote(), 8)
        tercas = [
            h for h in self.profissional.agenda.filter(automatico=False)
            if timezone.localtime(h.data_hora).hour == 14
        ]
        self.assertEqual(len(tercas), 8)

    def test_lote_com_conflito_manual_nao_cria_nem_altera_nada(self):
        horarios_padrao(self.profissional)
        criar_horario_individual(
            profissional=self.profissional, data=datetime(2026, 11, 3).date(), hora=time(14),
        )
        antes = list(self.profissional.agenda.values_list('pk', 'automatico'))
        with self.assertRaisesMessage(ValidationError, '03/11/2026 14:00'):
            self.lote()
        self.assertEqual(list(self.profissional.agenda.values_list('pk', 'automatico')), antes)

    def test_lote_repetido_nao_duplica(self):
        chave = uuid4()
        self.assertEqual(self.lote(chave=chave), 8)
        quantidade = self.profissional.agenda.count()
        self.assertEqual(self.lote(chave=chave), 0)
        self.assertEqual(self.profissional.agenda.count(), quantidade)

    def test_individual_assume_horario_da_grade_e_rejeita_repeticao(self):
        horarios_padrao(self.profissional)
        dados = {
            'profissional': self.profissional,
            'data': datetime(2026, 10, 28).date(),
            'hora': time(9),
        }
        quantidade = self.profissional.agenda.count()
        self.assertFalse(criar_horario_individual(**dados).automatico)
        self.assertEqual(self.profissional.agenda.count(), quantidade)
        with self.assertRaisesMessage(ValidationError, 'já está cadastrado'):
            criar_horario_individual(**dados)

    def test_cadastro_aceita_qualquer_dia_e_hora_futuros(self):
        criar_horario_individual(
            profissional=self.profissional, data=datetime(2026, 10, 31).date(), hora=time(12, 30),
        )
        self.assertEqual(self.lote(hora=time(20), semanas=2), 2)

    def test_horario_alem_de_trinta_dias_aparece_na_agenda_e_no_formulario(self):
        horario = criar_horario_individual(
            profissional=self.profissional, data=datetime(2027, 3, 2).date(), hora=time(9),
        )
        response = self.client.get(reverse('agendaProfissional'))
        self.assertIn(horario, response.context['horarios'])
        self.assertIn(horario, ConsultaForm(profissional=self.profissional).fields['agenda'].queryset)


SENHA_TESTE = 'Zx9!kLmQ2#vT'


def criar_profissional(apelido, crp):
    """Cria um profissional com usuário, para testes com sessão."""
    email = f'{apelido}@example.com'
    user = get_user_model().objects.create_user(
        username=email, email=email, password=SENHA_TESTE,
    )
    return Profissional.objects.create(
        user=user, nome=apelido.title(), email=email, telefone='87999990000', crp=crp,
    )


class CadastroProfissionalTests(TestCase):
    def dados(self, **extras):
        return {
            'nome': 'Carla Souza', 'email': 'carla@example.com',
            'telefone': '87999999999', 'crp': '02/12345',
            'senha': SENHA_TESTE, 'confirmarSenha': SENHA_TESTE, **extras,
        }

    def test_cadastro_valido_cria_usuario_e_normaliza_crp(self):
        response = self.client.post(reverse('cadastroProfissional'), self.dados())
        self.assertRedirects(response, reverse('login'))
        profissional = Profissional.objects.get()
        self.assertEqual(profissional.crp, '0212345')
        self.assertEqual(profissional.user.username, 'carla@example.com')

    def test_botao_tem_texto(self):
        self.assertContains(self.client.get(reverse('cadastroProfissional')), '>Cadastrar</button>')

    def test_crp_invalido(self):
        for crp in ('abc', '02/abc45', '02/123', '02/1234567', '///'):
            with self.subTest(crp=crp):
                form = ProfissionalFormCadastro(self.dados(crp=crp))
                self.assertFalse(form.is_valid())
                self.assertIn('crp', form.errors)

    def test_senha_diferente_fraca_ou_igual_ao_email(self):
        casos = (
            ({'confirmarSenha': 'outra'}, 'confirmarSenha'),
            ({'senha': '123', 'confirmarSenha': '123'}, 'senha'),
            ({'senha': 'carla@example.com', 'confirmarSenha': 'carla@example.com'}, 'senha'),
        )
        for extras, campo in casos:
            with self.subTest(extras=extras):
                form = ProfissionalFormCadastro(self.dados(**extras))
                self.assertFalse(form.is_valid())
                self.assertIn(campo, form.errors)

    def test_email_e_crp_duplicados_indicam_o_campo(self):
        criar_profissional('carla', '0212345')
        form = ProfissionalFormCadastro(self.dados(email='CARLA@example.com', crp='02-12345'))
        self.assertFalse(form.is_valid())
        self.assertIn('email', form.errors)
        self.assertIn('crp', form.errors)

    def test_corrida_pelo_crp_indica_o_campo_sem_usuario_orfao(self):
        form = ProfissionalFormCadastro(self.dados())
        self.assertTrue(form.is_valid())
        criar_profissional('outra', '0212345')
        with self.assertRaises(ValidationError) as contexto:
            form.save()
        self.assertEqual(list(contexto.exception.message_dict), ['crp'])
        self.assertFalse(get_user_model().objects.filter(username='carla@example.com').exists())


class LoginTests(TestCase):
    def setUp(self):
        criar_profissional('ana', '0211111')
        self.dados = {'email': 'ana@example.com', 'senha': SENHA_TESTE}

    def test_next_vai_ao_template_e_e_respeitado(self):
        destino = reverse('cadastroConsulta')
        response = self.client.get(reverse('login'), {'next': destino})
        self.assertContains(response, f'name="next" value="{destino}"')
        response = self.client.post(reverse('login'), {**self.dados, 'next': destino})
        self.assertRedirects(response, destino)

    def test_next_externo_e_ignorado(self):
        response = self.client.post(
            reverse('login'), {**self.dados, 'next': 'https://externo.example/'},
        )
        self.assertRedirects(response, reverse('index'))

    def test_credenciais_invalidas(self):
        response = self.client.post(reverse('login'), {**self.dados, 'senha': 'errada'})
        self.assertContains(response, 'Email ou senha inválidos!')
        self.assertNotIn('_auth_user_id', self.client.session)


class PerfilTests(TestCase):
    def setUp(self):
        self.ana = criar_profissional('ana', '0211111')
        self.bruno = criar_profissional('bruno', '0222222')
        self.client.force_login(self.ana.user)
        self.url = reverse('updatePerfilProfissional')

    def test_pagina_preenchida(self):
        response = self.client.get(self.url)
        self.assertContains(response, 'ana@example.com')
        self.assertContains(response, '>Salvar</button>')

    def test_atualiza_perfil_e_login_juntos(self):
        response = self.client.post(self.url, {'email': 'Nova@Example.com', 'telefone': '87911112222'})
        self.assertRedirects(response, self.url)
        self.ana.refresh_from_db()
        self.ana.user.refresh_from_db()
        self.assertEqual(self.ana.email, 'nova@example.com')
        self.assertEqual(self.ana.telefone, '87911112222')
        self.assertEqual(self.ana.user.username, 'nova@example.com')
        self.assertEqual(self.ana.user.email, 'nova@example.com')
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.client.logout()
        self.assertTrue(self.client.login(username='nova@example.com', password=SENHA_TESTE))

    def test_manter_o_proprio_email(self):
        response = self.client.post(self.url, {'email': 'ana@example.com', 'telefone': '87911112222'})
        self.assertRedirects(response, self.url)

    def test_email_de_outro_profissional_e_rejeitado(self):
        response = self.client.post(self.url, {'email': 'BRUNO@example.com', 'telefone': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertIn('email', response.context['form'].errors)
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.email, 'ana@example.com')

    def test_corrida_pelo_email_vira_erro_de_validacao(self):
        form = ProfissionalFormUpdate(
            {'email': 'novo@example.com', 'telefone': '1'}, instance=self.ana,
        )
        self.assertTrue(form.is_valid())
        get_user_model().objects.create_user(username='novo@example.com')
        with self.assertRaises(ValidationError):
            form.save()
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.email, 'ana@example.com')


class IsolamentoTests(TestCase):
    def setUp(self):
        self.ana = criar_profissional('ana', '0211111')
        self.bruno = criar_profissional('bruno', '0222222')
        self.paciente_bruno = Paciente.objects.create(
            profissional=self.bruno, nome='Paciente Sigiloso', telefone='87988887777',
        )
        self.horario_bruno = Agenda.objects.create(
            profissional=self.bruno, data_hora=timezone.now() + timedelta(days=60),
        )
        Consulta.objects.create(
            paciente=self.paciente_bruno, agenda=self.horario_bruno,
            data_hora=self.horario_bruno.data_hora,
        )
        self.client.force_login(self.ana.user)

    def test_nao_le_dados_de_outro_profissional(self):
        for nome in ('index', 'agendaProfissional', 'cadastroConsulta',
                     'gerenciarHorarios', 'updatePerfilProfissional'):
            with self.subTest(nome=nome):
                response = self.client.get(reverse(nome))
                self.assertNotContains(response, 'Paciente Sigiloso')
                self.assertNotContains(response, 'bruno@example.com')

    def test_dono_vem_da_sessao_e_ignora_id_enviado(self):
        self.client.post(reverse('cadastroPaciente'), {
            'nome': 'Novo', 'telefone': '87977776666', 'profissional': self.bruno.pk,
        })
        self.assertEqual(Paciente.objects.get(nome='Novo').profissional, self.ana)
        self.client.post(reverse('updatePerfilProfissional'), {
            'email': 'ana2@example.com', 'telefone': '1', 'profissional_id': self.bruno.pk,
        })
        self.bruno.refresh_from_db()
        self.assertEqual(self.bruno.email, 'bruno@example.com')


class PacienteOpcionaisTests(TestCase):
    def test_somente_nome_e_telefone(self):
        profissional = criar_profissional('ana', '0211111')
        self.client.force_login(profissional.user)
        response = self.client.post(
            reverse('cadastroPaciente'), {'nome': 'P', 'telefone': '(87) 99999-9999'},
        )
        self.assertRedirects(response, reverse('cadastroPaciente'))
        paciente = Paciente.objects.get()
        self.assertEqual((paciente.cpf, paciente.email, paciente.data_nascimento), ('', '', None))

    def test_telefone_e_nascimento_invalidos(self):
        for telefone in ('abc', '()-', '123'):
            with self.subTest(telefone=telefone):
                form = PacienteFormCadastro({'nome': 'P', 'telefone': telefone})
                self.assertFalse(form.is_valid())
                self.assertIn('telefone', form.errors)
        form = PacienteFormCadastro({
            'nome': 'P', 'telefone': '87999999999',
            'data_nascimento': timezone.localdate() + timedelta(days=1),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('data_nascimento', form.errors)


class CargaDeDadosTests(TestCase):
    def test_comandos_de_carga_podem_ser_repetidos(self):
        call_command('popular_banco', profissionais=2, stdout=StringIO())
        argumentos = {'profissionais': 2, 'pacientes': 5, 'consultas': 5, 'tratamentos': 3}
        call_command('seed_fake_data', stdout=StringIO(), **argumentos)
        call_command('seed_fake_data', clear=True, stdout=StringIO(), **argumentos)
        self.assertEqual(Profissional.objects.count(), 2)
        self.assertEqual(get_user_model().objects.count(), 2)
        for profissional in Profissional.objects.all():
            self.assertFalse(profissional.user.has_usable_password())
