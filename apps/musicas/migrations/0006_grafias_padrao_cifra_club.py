from django.db import migrations


def alinhar(apps, schema_editor):
    """Grafias padrão no padrão de cifragem do Cifra Club (C11 = tríade + 11ª, Cm5- = diminuto,
    C° = diminuto com sétima, C5 = power chord...). As grafias cadastradas pela equipe não mudam."""
    from apps.musicas.acordes import NOMES_PADRAO, normalizar_grafia

    NomeAcorde = apps.get_model('musicas', 'NomeAcorde')
    # 1. padroniza de novo (a regra de escrita mudou: ex. °7 agora é °) e junta repetidas
    grupos = {}
    for nome in NomeAcorde.objects.all():
        grupos.setdefault(normalizar_grafia(nome.escrita), []).append(nome)
    for forma, nomes in grupos.items():
        nomes.sort(key=lambda n: (n.origem != 'equipe', n.pk))
        manter, *repetidas = nomes
        for repetida in repetidas:
            repetida.delete()
        if manter.escrita != forma:
            manter.escrita = forma
            manter.save(update_fields=['escrita'])
    # 2. grafias padrão com o significado do Cifra Club (sem tocar nas da equipe)
    for escrita, tipo in NOMES_PADRAO.items():
        nome = NomeAcorde.objects.filter(escrita=escrita).first()
        if nome is None:
            NomeAcorde.objects.create(escrita=escrita, tipo=tipo, origem='padrao')
        elif nome.origem == 'padrao' and nome.tipo != tipo:
            nome.tipo = tipo
            nome.save(update_fields=['tipo'])


class Migration(migrations.Migration):

    dependencies = [
        ('musicas', '0005_normalizar_grafias'),
    ]

    operations = [
        migrations.RunPython(alinhar, migrations.RunPython.noop),
    ]
