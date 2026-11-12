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


NOMES_NOTAS = ['C', 'C#', 'D', 'Eb', 'E', 'F', 'F#', 'G', 'Ab', 'A', 'Bb', 'B']


class DesenhoAcorde(models.Model):
    """Um desenho (posição) de acorde no braço do instrumento. O "Variar" passa pelos desenhos na ordem."""

    INSTRUMENTOS = [('violao', 'Violão / guitarra')]
    ORIGENS = [('base', 'Base pública (chords-db)'), ('equipe', 'Cadastrado pela equipe')]

    instrumento = models.CharField(max_length=20, choices=INSTRUMENTOS, default='violao')
    raiz = models.PositiveSmallIntegerField(help_text="Nota do acorde: 0 = C, 1 = C#, ..., 11 = B")
    tipo = models.CharField(max_length=20, help_text="major, minor, sus4, add9, m7, maj7...")
    baixo = models.PositiveSmallIntegerField(null=True, blank=True,
                                             help_text="Nota do baixo quando diferente (D/F# -> 6)")
    casas = models.JSONField(help_text="Casa de cada corda, da 6ª (Mi grave) para a 1ª; -1 = não toca, 0 = solta")
    dedos = models.JSONField(default=list, blank=True, help_text="Dedo de cada corda (0 = nenhum)")
    pestanas = models.JSONField(default=list, blank=True, help_text="Casas com pestana")
    ordem = models.PositiveSmallIntegerField(default=1)
    origem = models.CharField(max_length=10, choices=ORIGENS, default='equipe')
    ativo = models.BooleanField(default=True)

    class Meta:
        ordering = ['instrumento', 'raiz', 'tipo', 'baixo', 'ordem', 'id']
        indexes = [models.Index(fields=['instrumento', 'raiz', 'tipo'])]

    def __str__(self):
        baixo = f'/{NOMES_NOTAS[self.baixo]}' if self.baixo is not None else ''
        casas = ' '.join('x' if c < 0 else str(c) for c in self.casas)
        return f'{NOMES_NOTAS[self.raiz]} {self.tipo}{baixo} [{casas}]'


class NomeAcorde(models.Model):
    """Como a equipe escreve o tipo do acorde depois da nota: "4" = sus4, "7M" = maj7, "4/7" = 7sus4..."""

    escrita = models.CharField(max_length=20, unique=True, blank=True,
                               help_text='O que vem depois da nota (ex.: "4", "7M", "m7(b5)"); vazio = maior')
    tipo = models.CharField(max_length=20, help_text="Tipo correspondente nos desenhos (sus4, maj7...)")
    origem = models.CharField(max_length=10, choices=[('padrao', 'Padrão'), ('equipe', 'Equipe')], default='equipe')

    class Meta:
        ordering = ['tipo', 'escrita']

    def __str__(self):
        return f'"{self.escrita}" = {self.tipo}'
