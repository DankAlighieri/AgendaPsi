from django import forms
from django.db.models import Exists, OuterRef
from .models import Agenda, Consulta, Paciente, Profissional
from .services import horarios_padrao

# class ProfissionalForm(forms.Form):
#         nome = forms.CharField(
#             label = "nome",
#             max_length = 100
#         )
#         email = forms.CharField(
#             label = "email",
#             max_length = 100
#         )
#         telefone = forms.CharField(
#             label = "telefone",
#             max_length = 100
#         )
#         crp = forms.CharField(
#             label = "crp",
#             max_length = 100
#         )

###
# Reutilizando o modelo de dados ja definido
class ProfissionalForm(forms.ModelForm):
    class Meta:
        model = Profissional
        fields = ["nome", "email", "telefone", "crp"]


class ConsultaForm(forms.Form):
    paciente = forms.ModelChoiceField(
        label='Cliente', queryset=Paciente.objects.none(), empty_label='Selecione o cliente'
    )
    agenda = forms.ModelChoiceField(
        label='Horário disponível', queryset=Agenda.objects.none(),
        empty_label='Selecione o horário',
    )

    def __init__(self, *args, profissional, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['paciente'].queryset = profissional.pacientes.order_by('nome')
        ocupadas = Consulta.objects.filter(
            paciente__profissional=profissional, data_hora=OuterRef('data_hora')
        ).exclude(status=Consulta.Status.CANCELADA)
        self.fields['agenda'].queryset = horarios_padrao(profissional).annotate(
            reservado=Exists(ocupadas)
        ).filter(reservado=False).select_related('profissional')
        self.fields['agenda'].error_messages['invalid_choice'] = (
            'Este horário não está disponível. Escolha outro horário da lista.'
        )
