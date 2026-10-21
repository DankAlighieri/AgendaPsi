from django.contrib import admin
from .models import Agenda, Profissional, Paciente, Consulta, Tratamento


class PacienteInline(admin.TabularInline):
    model = Paciente
    extra = 0


class ConsultaInline(admin.TabularInline):
    model = Consulta
    extra = 0


class TratamentoInline(admin.TabularInline):
    model = Tratamento
    extra = 0


@admin.register(Profissional)
class ProfissionalAdmin(admin.ModelAdmin):
    list_display = ('nome', 'email', 'telefone', 'crp')
    search_fields = ('nome', 'email', 'crp')
    inlines = [PacienteInline]


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'profissional', 'telefone', 'email')
    list_filter = ('profissional',)
    search_fields = ('nome', 'email')
    inlines = [ConsultaInline]


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_hora', 'status')
    list_filter = ('status', 'data_hora')
    search_fields = ('paciente__nome',)
    inlines = [TratamentoInline]


@admin.register(Agenda)
class AgendaAdmin(admin.ModelAdmin):
    list_display = ('profissional', 'data_hora', 'ocupado')
    list_filter = ('profissional', 'data_hora')
    search_fields = ('profissional__nome',)

    @admin.display(boolean=True, description='Ocupado')
    def ocupado(self, obj):
        return obj.ocupado

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.consultas.exists():
            return ('profissional', 'data_hora')
        return ()


@admin.register(Tratamento)
class TratamentoAdmin(admin.ModelAdmin):
    list_display = (
        'consulta',
        'data_inicio',
        'data_fim_prevista',
        'frequencia',
        'ativo',
    )
    list_filter = ('frequencia', 'ativo')
