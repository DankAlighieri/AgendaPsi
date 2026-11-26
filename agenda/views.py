from uuid import uuid4
from django.http import HttpResponseBadRequest
from django.utils import timezone
from .forms import ConsultaForm, HorarioIndividualForm, HorariosLoteForm, LoginForm, ProfissionalFormCadastro, PacienteFormCadastro
from .models import Agenda, Consulta, Profissional
from .services import agendar_consulta, criar_horario_individual, criar_horarios_lote, horarios_padrao
from .decorators import profissional_required
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.utils.http import url_has_allowed_host_and_scheme
from django.urls import reverse

@profissional_required
def index(req):
    profissional = req.profissional
    consultas = Consulta.objects.filter(
        paciente__profissional=profissional, data_hora=OuterRef('data_hora')
    ).exclude(status=Consulta.Status.CANCELADA)
    horarios = horarios_padrao(profissional).annotate(
        reservado=Exists(consultas)
    )
    return render(req, 'agenda.html', {
        'profissional': profissional, 'horarios': horarios,
        'consultas': Consulta.objects.filter(
            paciente__profissional=profissional
        ).select_related('paciente').order_by('data_hora'),
    }) 

def cadastroProfissional(req):
    if req.method == "POST":
        form = ProfissionalFormCadastro(req.POST)
        if form.is_valid():
            try:
                form.save()
            except ValidationError as exec:
                form.add_error(None, exec)
            else:
                messages.success(req, "Cadastro efetuado com sucesso!")
                return redirect("login")
    else:
        form = ProfissionalFormCadastro()
    return render(req, "cadastro.html", {
        "form": form,
        "titulo": "Cadastro do profissional",
        "subtitulo": "Preencha seus dados.",
        "link_url": reverse("index"),
        "link_texto": "Voltar à agenda",
        })

def loginProfissional(req):
    if req.method == "POST":
        form = LoginForm(req.POST)
        destino = req.POST.get("next") or req.GET.get("next") or ""
        if form.is_valid():
            username = form.cleaned_data["email"].strip().lower()
            senha = form.cleaned_data["senha"]
            user = authenticate(req, username = username, password = senha)
            if user is not None and hasattr(user, "profissional"):
                login(req, user)
                if url_has_allowed_host_and_scheme(destino, allowed_hosts={req.get_host()}):
                    return redirect(destino)
                return redirect("index")
            else:
                form.add_error(None, "Email ou senha inválidos!")
    else:
        form = LoginForm()
    return render(req, "login.html", {"form":form})

## TODO: Metodo de logout
@profissional_required
def cadastroPaciente(req):
    form = PacienteFormCadastro(
        req.POST if req.method == "POST" else None
    )

    if req.method == "POST" and form.is_valid():
            paciente = form.save(commit=False)
            paciente.profissional = req.profissional
            paciente.save()

            messages.success(req, "Paciente cadastrado")
            return redirect("cadastroPaciente")

    return render(req, "cadastro.html", {
            "form": form,
            "titulo": "Cadastro de paciente",
            "subtitulo": "Preencha os dados do paciente.",
            "link_url": reverse("index"),
            "link_texto": "Voltar à agenda",
            "texto_botao": "Salvar",
        })

@profissional_required
def agenda_profissional(req):
    profissional = req.profissional
    consultas = Consulta.objects.filter(
        paciente__profissional=profissional, data_hora=OuterRef('data_hora')
    ).exclude(status=Consulta.Status.CANCELADA)
    horarios = horarios_padrao(profissional).annotate(
        reservado=Exists(consultas)
    )
    return render(req, 'agenda.html', {
        'profissional': profissional, 'horarios': horarios,
        'consultas': Consulta.objects.filter(
            paciente__profissional=profissional
        ).select_related('paciente').order_by('data_hora'),
    }) 

@profissional_required
def cadastro_consulta(req):
    profissional = req.profissional
    form = ConsultaForm(req.POST if req.method == 'POST' else None, profissional=profissional)
    if req.method == 'POST' and form.is_valid():
        try:
            agendar_consulta(
                profissional=profissional, paciente=form.cleaned_data['paciente'],
                horario=form.cleaned_data['agenda'],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(req, 'Consulta agendada com sucesso! O horário está ocupado.')
            return redirect('agendaProfissional')
    return render(req, 'consulta.html', {'profissional': profissional, 'form': form})

@profissional_required
def gerenciar_horarios(req):
    profissional = req.profissional

    form_individual = HorarioIndividualForm()
    form_lote = HorariosLoteForm(
        initial={'chave_idempotencia': uuid4()}
    )

    if req.method == 'POST':
        tipo = req.POST.get('tipo')

        if tipo == 'individual':
            form_individual = HorarioIndividualForm(req.POST)

            if form_individual.is_valid():
                try:
                    criar_horario_individual(
                        profissional=profissional,
                        data=form_individual.cleaned_data['data'],
                        hora=form_individual.cleaned_data['hora'],
                    )
                except ValidationError as exc:
                    form_individual.add_error(None, exc)
                else:
                    messages.success(req, 'Horário cadastrado.')
                    return redirect('gerenciarHorarios')

        elif tipo == 'lote':
            form_lote = HorariosLoteForm(req.POST)

            if form_lote.is_valid():
                try:
                    quantidade = criar_horarios_lote(
                        profissional=profissional,
                        data_inicio=form_lote.cleaned_data['data_inicio'],
                        dia_semana=int(form_lote.cleaned_data['dia_semana']),
                        hora=form_lote.cleaned_data['hora'],
                        semanas=form_lote.cleaned_data['semanas'],
                        chave_idempotencia=form_lote.cleaned_data[
                            'chave_idempotencia'
                        ],
                    )
                except ValidationError as exc:
                    form_lote.add_error(None, exc)
                else:
                    if quantidade:
                        messages.success(
                            req,
                            f'{quantidade} horários cadastrados.',
                        )
                    else:
                        messages.info(
                            req,
                            'Este lote já havia sido processado.',
                        )
                    return redirect('gerenciarHorarios')

        else:
            return HttpResponseBadRequest('Tipo de cadastro inválido.')

    horarios_padrao(profissional)  # Mantém a criação automática dos horários padrão.

    consultas_ativas = Consulta.objects.filter(
        paciente__profissional=profissional,
        data_hora=OuterRef('data_hora'),
    ).exclude(status=Consulta.Status.CANCELADA)

    horarios = Agenda.objects.filter(
        profissional=profissional,
        data_hora__gt=timezone.now(),
    ).annotate(
        reservado=Exists(consultas_ativas)
    ).order_by('data_hora')

    return render(req, 'gerenciar_horarios.html', {
        'form_individual': form_individual,
        'form_lote': form_lote,
        'horarios': horarios,
    })
