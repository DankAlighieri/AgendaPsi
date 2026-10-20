from .forms import ProfissionalForm
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render, redirect
from django.contrib import messages

def index(req):
    return HttpResponse("Ola")

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