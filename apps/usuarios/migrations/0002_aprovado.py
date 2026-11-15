from django.db import migrations, models


def marcar_pendentes(apps, schema_editor):
    """Até aqui, "inativo" significava "cadastro aguardando aprovação": esses ficam como não aprovados."""
    apps.get_model('usuarios', 'Usuario').objects.filter(is_active=False).update(aprovado=False)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usuario',
            name='aprovado',
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(marcar_pendentes, migrations.RunPython.noop),
    ]
