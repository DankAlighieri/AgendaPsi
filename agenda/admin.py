from django.contrib import admin
from .models import (
    Agenda,
    Atividade,
    Consulta,
    ObjetivoTerapeutico,
    ObservacaoConsulta,
    Paciente,
    Profissional,
    Tratamento,
)


class PacienteInline(admin.TabularInline):
    model = Paciente
    extra = 0


class ConsultaInline(admin.TabularInline):
    model = Consulta
    extra = 0


class TratamentoInline(admin.TabularInline):
    model = Tratamento
    extra = 0


class AtividadeInline(admin.TabularInline):
    model = Atividade
    extra = 0


class ObservacaoConsultaInline(admin.TabularInline):
    model = ObservacaoConsulta
    extra = 0


class ObjetivoTerapeuticoInline(admin.TabularInline):
    model = ObjetivoTerapeutico
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
    inlines = [ConsultaInline, TratamentoInline]


@admin.register(Consulta)
class ConsultaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'data_hora', 'status')
    list_filter = ('status', 'data_hora')
    search_fields = ('paciente__nome',)
    inlines = [AtividadeInline, ObservacaoConsultaInline]


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
        'paciente',
        'data_inicio',
        'data_fim_prevista',
        'frequencia',
        'ativo',
    )
    list_filter = ('frequencia', 'ativo')
    inlines = [ObjetivoTerapeuticoInline]


@admin.register(Atividade)
class AtividadeAdmin(admin.ModelAdmin):
    list_display = ('consulta', 'atividade')
    search_fields = ('atividade',)


@admin.register(ObservacaoConsulta)
class ObservacaoConsultaAdmin(admin.ModelAdmin):
    list_display = ('consulta', 'tipo', 'observacao', 'data_registro')
    list_filter = ('tipo', 'data_registro')


@admin.register(ObjetivoTerapeutico)
class ObjetivoTerapeuticoAdmin(admin.ModelAdmin):
    list_display = ('tratamento', 'descricao', 'status')
    list_filter = ('status',)
