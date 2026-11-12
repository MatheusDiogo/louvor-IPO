from django.db import migrations, models


def tirar_baixo(apps, schema_editor):
    """Os desenhos de baixo foram retirados: instrumentos marcados como "Baixo" voltam para "Não definido"."""
    apps.get_model('instrumentos', 'Instrumento').objects.filter(desenho='baixo').update(desenho='')


class Migration(migrations.Migration):

    dependencies = [
        ('instrumentos', '0003_desenho_de_acorde'),
    ]

    operations = [
        migrations.RunPython(tirar_baixo, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='instrumento',
            name='desenho',
            field=models.CharField(blank=True, choices=[('', 'Não definido'), ('violao', 'Violão / guitarra'), ('teclado', 'Teclado'), ('nenhum', 'Nenhum (ex.: voz)')], default='', help_text='Desenhos de acorde mostrados para quem toca este instrumento', max_length=10),
        ),
    ]
