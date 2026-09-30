from django.shortcuts import render
from django.http import HttpResponse

def index(req):
    return HttpResponse("Ola");

# def  cadastro(req):
    