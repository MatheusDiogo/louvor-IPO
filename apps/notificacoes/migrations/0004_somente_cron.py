from django.db import migrations, models


def apagar_avisos_do_prazo(apps, schema_editor):
    """Os avisos da disponibilidade não vêm mais pré-cadastrados: o administrador cria na tela, por cron."""
    apps.get_model('notificacoes', 'AvisoProgramado').objects.filter(agenda='prazo').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0003_avisos_da_disponibilidade'),
    ]

    operations = [
        migrations.RunPython(apagar_avisos_do_prazo, migrations.RunPython.noop),
        migrations.RemoveField(model_name='avisoprogramado', name='agenda'),
        migrations.RemoveField(model_name='avisoprogramado', name='dias_antes_prazo'),
        migrations.RemoveField(model_name='avisoprogramado', name='hora'),
        migrations.AlterField(
            model_name='avisoprogramado',
            name='cron',
            field=models.CharField(help_text='minuto hora dia mês dia-da-semana', max_length=100),
        ),
    ]
