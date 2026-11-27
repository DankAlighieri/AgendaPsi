from django.urls import path
from . import views

urlpatterns = [
    path('agenda/', views.agenda_profissional, name='agendaProfissional'),
    path('consultas/nova/', views.cadastro_consulta, name='cadastroConsulta'),
    path('agenda/horarios/', views.gerenciar_horarios,name='gerenciarHorarios'),
    path('cadastroPaciente', views.cadastroPaciente, name='cadastroPaciente'),
    path('updatePerfil', views.updatePerfilProfissional, name='updatePerfilProfissional')
]