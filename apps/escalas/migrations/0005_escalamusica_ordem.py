from django.db import migrations, models


def numerar_existentes(apps, schema_editor):
    """Mantém a ordem atual (ordem de inclusão) das músicas já cadastradas."""
    EscalaMusica = apps.get_model('escalas', 'EscalaMusica')
    posicoes = {}
    for item in EscalaMusica.objects.order_by('escala_id', 'id'):
        posicoes[item.escala_id] = posicoes.get(item.escala_id, 0) + 1
        item.ordem = posicoes[item.escala_id]
        item.save(update_fields=['ordem'])


class Migration(migrations.Migration):

    dependencies = [
        ('escalas', '0004_publicacaoescala'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='escalamusica',
            options={'ordering': ['ordem', 'id']},
        ),
        migrations.AddField(
            model_name='escalamusica',
            name='ordem',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.RunPython(numerar_existentes, migrations.RunPython.noop),
    ]
