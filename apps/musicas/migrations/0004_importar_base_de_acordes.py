from django.db import migrations


def importar(apps, schema_editor):
    """Preenche a tabela com os desenhos da base pública (chords-db) e os nomes padrão."""
    from apps.musicas.acordes import importar_base
    importar_base(apps.get_model('musicas', 'DesenhoAcorde'), apps.get_model('musicas', 'NomeAcorde'))


def desfazer(apps, schema_editor):
    apps.get_model('musicas', 'DesenhoAcorde').objects.filter(origem='base').delete()
    apps.get_model('musicas', 'NomeAcorde').objects.filter(origem='padrao').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('musicas', '0003_desenhos_de_acordes'),
    ]

    operations = [
        migrations.RunPython(importar, desfazer),
    ]
