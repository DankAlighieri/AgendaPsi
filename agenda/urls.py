from django.urls import path
from . import views

urlpatterns = [
    path('profissionais/<int:profissional_id>/agenda/', views.agenda_profissional, name='agendaProfissional'),
    path('profissionais/<int:profissional_id>/consultas/nova/', views.cadastro_consulta, name='cadastroConsulta'),
]
