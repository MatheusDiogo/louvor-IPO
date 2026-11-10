from django.db import models


class Musica(models.Model):

    nome = models.CharField(
        max_length=200
    )

    tom = models.CharField(
        max_length=10,
        blank=True,
        help_text="Tom original em que a cifra foi escrita (ex.: G, Dm)"
    )

    cifra = models.TextField(
        blank=True,
        help_text="Cifra no formato ChordPro"
    )

    link_youtube = models.URLField(
        blank=True,
        null=True
    )

    # Importada automaticamente e ainda não conferida por um líder
    revisar = models.BooleanField(default=False)

    atualizado_em = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.nome
