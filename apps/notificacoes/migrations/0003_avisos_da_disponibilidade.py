from django.db import migrations

CONSULTA = """-- Todos os integrantes ativos
SELECT id FROM usuarios_usuario WHERE is_active"""


def criar(apps, schema_editor):
    """Os dois avisos do prazo da disponibilidade já vêm cadastrados (dá para editar ou pausar na tela)."""
    AvisoProgramado = apps.get_model('notificacoes', 'AvisoProgramado')
    AvisoProgramado.objects.get_or_create(nome='Disponibilidade: segunda da semana do prazo', defaults=dict(
        agenda='prazo', dias_antes_prazo=4, hora=9, url='/escalas/disponibilidade/', consulta=CONSULTA,
        titulo='Disponibilidade de {mes_seguinte}',
        mensagem='Oi {nome}! Informe os dias de {mes_seguinte} em que você não pode servir até sexta ({prazo}). '
                 'Toque para abrir.',
    ))
    AvisoProgramado.objects.get_or_create(nome='Disponibilidade: último dia (sexta)', defaults=dict(
        agenda='prazo', dias_antes_prazo=0, hora=9, url='/escalas/disponibilidade/', consulta=CONSULTA,
        titulo='Último dia: disponibilidade de {mes_seguinte}',
        mensagem='Hoje é o último dia para informar os dias de {mes_seguinte} em que você não pode servir.',
    ))


class Migration(migrations.Migration):

    dependencies = [
        ('notificacoes', '0002_avisos_programados'),
    ]

    operations = [
        migrations.RunPython(criar, migrations.RunPython.noop),
    ]
