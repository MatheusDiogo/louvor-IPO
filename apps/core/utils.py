import unicodedata


def chave_alfabetica(texto):
    """Chave de ordenação que ignora acentos e maiúsculas (o SQLite ordena por bytes)."""
    sem_acento = unicodedata.normalize('NFD', texto or '').encode('ascii', 'ignore').decode()
    return sem_acento.casefold()
