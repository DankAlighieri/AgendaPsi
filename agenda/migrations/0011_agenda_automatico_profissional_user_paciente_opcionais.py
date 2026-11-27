from django.conf import settings
from django.db import migrations, models
from django.utils import timezone

HORAS_DA_GRADE = (8, 9, 10, 11, 14, 15, 16, 17)


def marcar_horarios_da_grade(apps, schema_editor):
    """Até aqui só a grade era usada na prática: marca o que se encaixa nela."""
    Agenda = apps.get_model('agenda', 'Agenda')
    db = schema_editor.connection.alias
    fuso = timezone.get_default_timezone()

    ids = []
    for pk, data_hora in Agenda.objects.using(db).values_list('pk', 'data_hora'):
        local = timezone.localtime(data_hora, fuso)
        if (
            local.weekday() < 5 and local.hour in HORAS_DA_GRADE
            and local.minute == local.second == local.microsecond == 0
        ):
            ids.append(pk)

    for inicio in range(0, len(ids), 500):
        Agenda.objects.using(db).filter(
            pk__in=ids[inicio:inicio + 500]
        ).update(automatico=True)


class Migration(migrations.Migration):

    dependencies = [
        ('agenda', '0010_backfill_profissional_user_e_crp'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='paciente',
            name='paciente_email_preenchido',
        ),
        migrations.AddField(
            model_name='agenda',
            name='automatico',
            field=models.BooleanField(default=False, verbose_name='Gerado pela grade'),
        ),
        migrations.RunPython(marcar_horarios_da_grade, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='paciente',
            name='cpf',
            field=models.CharField(blank=True, max_length=14),
        ),
        migrations.AlterField(
            model_name='paciente',
            name='email',
            field=models.EmailField(blank=True, max_length=254),
        ),
        migrations.AlterField(
            model_name='profissional',
            name='user',
            field=models.OneToOneField(on_delete=models.deletion.CASCADE, related_name='profissional', to=settings.AUTH_USER_MODEL),
        ),
    ]
