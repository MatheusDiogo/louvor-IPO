from django.db import models


class Musica(models.Model):

    nome = models.CharField(
        max_length=200
    )

    link_youtube = models.URLField(
        blank=True,
        null=True
    )

    def __str__(self):
        return self.nome
    
class Tom(models.Model):

    musica = models.ForeignKey(
        Musica,
        on_delete=models.CASCADE,
        related_name="tons"
    )

    tom = models.CharField(
        max_length=10
    )

    cifra_base64 = models.TextField()

    def __str__(self):
        return f"{self.musica.nome} - {self.tom}"