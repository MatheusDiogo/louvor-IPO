from django.contrib.auth.models import AbstractUser
from django.db import models
from apps.instrumentos.models import Instrumento

class Usuario(AbstractUser):

    instrumentos = models.ManyToManyField(
        Instrumento,
        blank=True,
        related_name="musicos"
    )

    email = models.EmailField(
        unique=True
    )

    is_lider = models.BooleanField(
        default=False
    )

    def __str__(self):
        return self.get_full_name() or self.username