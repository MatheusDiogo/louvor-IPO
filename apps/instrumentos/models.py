from django.db import models


class Instrumento(models.Model):

    nome = models.CharField(
        max_length=100,
        unique=True
    )

    ordem = models.PositiveIntegerField(
        default=0,
        help_text="Posição da coluna na escala de integrantes"
    )

    # Quais desenhos de acorde mostrar para quem está escalado neste instrumento
    DESENHOS = [
        ('', 'Não definido'),
        ('violao', 'Violão / guitarra'),
        ('teclado', 'Teclado'),
        ('nenhum', 'Nenhum (ex.: voz)'),
    ]
    desenho = models.CharField(
        max_length=10,
        choices=DESENHOS,
        blank=True,
        default='',
        help_text="Desenhos de acorde mostrados para quem toca este instrumento"
    )

    class Meta:
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome
