from .forms import ConsultaForm, ProfissionalForm
from .models import Consulta, Profissional
from .services import agendar_consulta, horarios_padrao
from django.core.exceptions import ValidationError
from django.db.models import Exists, OuterRef
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages

def index(req):
    return render(req, 'profissionais.html', {
        'profissionais': Profissional.objects.order_by('nome'),
    })

def teste(req):
    return HttpResponse("Teste bem sucessido")

def cadastroProfissional(req):
    if req.method == "POST":
        form = ProfissionalForm(req.POST)
        if form.is_valid():
            form.save()
            messages.success(req, "Cadastro efetuado com sucesso!")
            return redirect("cadastroProfissional")
    else:
        form = ProfissionalForm()
    return render(req, "cadastro.html", {"form": form})


def agenda_profissional(req, profissional_id):
    profissional = get_object_or_404(Profissional, pk=profissional_id)
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


def cadastro_consulta(req, profissional_id):
    profissional = get_object_or_404(Profissional, pk=profissional_id)
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
