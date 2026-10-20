from django import forms
from .models import Profissional

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