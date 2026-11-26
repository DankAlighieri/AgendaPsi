from django.urls import path
from . import views

urlpatterns = [
    path('agenda/', views.agenda_profissional, name='agendaProfissional'),
    path('consultas/nova/', views.cadastro_consulta, name='cadastroConsulta'),
]
