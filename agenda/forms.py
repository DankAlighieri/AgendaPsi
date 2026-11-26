import uuid
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.db import transaction, IntegrityError
from django.db.models import Exists, OuterRef
from django.utils import timezone
from .models import Agenda, Consulta, Paciente, Profissional
from .services import MAX_SEMANAS_LOTE, horario_de_atendimento, horarios_padrao

###
# Reutilizando o modelo de dados ja definido

class PacienteFormCadastro(forms.ModelForm):

    data_nascimento = forms.DateField(
        label="Data de nascimento",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={
            "placeholder": "000.000.000-00",
            "inputmode": "numeric",
            "autocomplete": "off",
        }),
    )
    nome = forms.CharField(
        label="Nome",
        max_length=150,
    )
    telefone = forms.CharField(
        label="Telefone",  
        max_length=20,
        widget=forms.TextInput(attrs={
            "placeholder": "(00) 00000-0000",
            "inputmode": "numeric",
            "autocomplete": "off",
        }),
    )
    email = forms.EmailField(
        label="Email",
        max_length=254,
        required=True,
    )

    class Meta:
        model = Paciente
        fields = ["data_nascimento","cpf","nome","telefone","email"]

    def clean_cpf(self):
        cpf = self.cleaned_data["cpf"].strip().replace(".", "").replace("-", "").replace(" ", "")
        ## TODO: Fazer esta mesma validação para o CRP
        if (
            len(cpf) != 11
            or not cpf.isascii()
            or not cpf.isdigit()
            or cpf == cpf[0] * 11
        ):
            raise forms.ValidationError("Informe um CPF válido.")

        digitos = [int(digito) for digito in cpf]
        soma = sum(digito * peso for digito, peso in zip(digitos[:9], range(10, 1, -1)))
        primeiro = (soma * 10) % 11
        if primeiro == 10:
            primeiro = 0

        soma = sum(digito * peso for digito, peso in zip(digitos[:10], range(11, 1, -1)))
        segundo = (soma * 10) % 11
        if segundo == 10:
            segundo = 0

        if digitos[9:] != [primeiro, segundo]:
            raise forms.ValidationError("Informe um CPF válido.")

        return cpf
    
    def clean_telefone(self):
        return self.cleaned_data["telefone"].strip().replace("(", "").replace(")", "").replace("-", "").replace(" ", "") 
    
    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()
    
    def clean_data_nascimento(self):
        data = self.cleaned_data.get("data_nascimento")
        if not data:
            raise forms.ValidationError("Adicione uma data de nascimento")
        return data
    #chamar o form.is_valid() na view

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
        horarios_padrao(profissional)

        self.fields['agenda'].queryset = Agenda.objects.filter(
            profissional=profissional,
            data_hora__gt=timezone.now(),
        ).annotate(
            reservado=Exists(ocupadas)
        ).filter(
            reservado=False
        ).select_related('profissional')
        self.fields['agenda'].error_messages['invalid_choice'] = (
            'Este horário não está disponível. Escolha outro horário da lista.'
        )

    def clean_agenda(self):
        agenda = self.cleaned_data['agenda']
        if not horario_de_atendimento(agenda.data_hora):
            raise forms.ValidationError(
                'Selecione um horário de segunda a sexta, das 8h às 12h ou das 14h às 18h.'
            )
        return agenda


class HorarioIndividualForm(forms.Form):
    data = forms.DateField(
        label='Data',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    hora = forms.TimeField(
        label='Horário',
        input_formats=['%H:%M'],
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
    )


class HorariosLoteForm(forms.Form):
    DIAS_DA_SEMANA = (
        ('0', 'Segunda-feira'),
        ('1', 'Terça-feira'),
        ('2', 'Quarta-feira'),
        ('3', 'Quinta-feira'),
        ('4', 'Sexta-feira'),
        ('5', 'Sábado'),
        ('6', 'Domingo'),
    )

    data_inicio = forms.DateField(
        label='A partir de',
        widget=forms.DateInput(attrs={'type': 'date'}),
    )
    dia_semana = forms.ChoiceField(
        label='Dia da semana',
        choices=DIAS_DA_SEMANA,
    )
    hora = forms.TimeField(
        label='Horário',
        input_formats=['%H:%M'],
        widget=forms.TimeInput(attrs={'type': 'time'}, format='%H:%M'),
    )
    semanas = forms.IntegerField(
        label='Quantidade de semanas',
        min_value=1,
        max_value=MAX_SEMANAS_LOTE,
    )
    chave_idempotencia = forms.UUIDField(
        widget=forms.HiddenInput,
    )
