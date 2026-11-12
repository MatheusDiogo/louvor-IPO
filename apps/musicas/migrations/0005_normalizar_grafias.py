from django.db import migrations


def normalizar(apps, schema_editor):
    """Junta as grafias que só mudam na forma de escrever (7(9) = 7/9 = 79) numa só, já normalizada."""
    from apps.musicas.acordes import normalizar_grafia

    NomeAcorde = apps.get_model('musicas', 'NomeAcorde')
    grupos = {}
    for nome in NomeAcorde.objects.all():
        grupos.setdefault(normalizar_grafia(nome.escrita), []).append(nome)
    for forma, nomes in grupos.items():
        # fica a da equipe (se houver); as outras saem
        nomes.sort(key=lambda n: (n.origem != 'equipe', n.pk))
        manter, *repetidas = nomes
        for repetida in repetidas:
            repetida.delete()
        if manter.escrita != forma:
            manter.escrita = forma
            manter.save(update_fields=['escrita'])


class Migration(migrations.Migration):

    dependencies = [
        ('musicas', '0004_importar_base_de_acordes'),
    ]

    operations = [
        migrations.RunPython(normalizar, migrations.RunPython.noop),
    ]
