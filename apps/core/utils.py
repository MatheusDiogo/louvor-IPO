import unicodedata


def chave_alfabetica(texto):
    """Chave de ordenação que ignora acentos e maiúsculas (o SQLite ordena por bytes)."""
    sem_acento = unicodedata.normalize('NFD', texto or '').encode('ascii', 'ignore').decode()
    return sem_acento.casefold()


def subtrair_meses(data, meses):
    """Mesma data `meses` meses antes (ajusta o dia no fim do mês: 31/05 - 3 meses = 28/02)."""
    import calendar
    total = data.year * 12 + (data.month - 1) - meses
    ano, mes = divmod(total, 12)
    mes += 1
    return data.replace(year=ano, month=mes, day=min(data.day, calendar.monthrange(ano, mes)[1]))
