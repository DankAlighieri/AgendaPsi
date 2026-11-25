from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError
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
class ProfissionalFormCadastro(forms.ModelForm):
    senha = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput # esconder input com *
    )

    confirmarSenha = forms.CharField(
        label="Confirmar Senha",
        widget=forms.PasswordInput
    )

    class Meta:
        model = Profissional
        fields = ["nome", "email", "telefone", "crp"]

    def clean_crp(self):
        return self.cleaned_data["crp"].strip().replace("/","").replace(".", "").replace("-", "").replace(" ", "") # normalizacao da besta fera

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        User = get_user_model()

        if Profissional.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Já existe um profissional com este e-mail.")

        if User.objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("Este e-mail não pode ser usado.")

        return email

    def clean(self):
        cleaned = super().clean()
        senha = cleaned.get("senha")

        if senha and senha != cleaned.get("confirmarSenha"):
            self.add_error("confirmarSenha", "As senhas não são iguais!")
        elif senha:
            try:
                validate_password(senha)
            except forms.ValidationError as exec:
                self.add_error("senha", exec)
        return cleaned

    def save(self, commit=True):
        profissional = super().save(commit=False)
        User = get_user_model()

        try:
            with transaction.atomic():
                user = User.objects.create_user(
                    username=self.cleaned_data["email"],
                    email=self.cleaned_data["email"],
                    password=self.cleaned_data["senha"]
                )
                profissional.user = user
                if commit:
                    profissional.save()
        ##TODO: 
        # Especificar qual dualidade realmente ocorreu (email ou crp) ou se foi outro erro (erro de cadastro no servidor)
        except IntegrityError:
            raise forms.ValidationError("Este profissional já existe")
        return profissional
    
class LoginForm(forms.Form):
    email = forms.CharField(
        label="email",
        max_length=100
    )

    senha = forms.CharField(
        label="senha",
        widget=forms.PasswordInput
    )  

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
