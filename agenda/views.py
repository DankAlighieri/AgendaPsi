from .forms import ConsultaForm, ProfissionalFormCadastro, LoginForm
from .models import Consulta, Profissional
from .services import agendar_consulta, horarios_padrao
from .decorators import profissional_required
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.utils.http import url_has_allowed_host_and_scheme

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
    return render(req, "cadastro.html", {"form": form})

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
            return redirect('agendaProfissional', profissional_id=profissional.pk)
    return render(req, 'consulta.html', {'profissional': profissional, 'form': form})
