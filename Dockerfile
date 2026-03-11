# Usa a imagem oficial do Python (versão estável)
FROM python:3.11-slim

# Define variáveis de ambiente para o Python não gerar arquivos .pyc e não bufferizar logs
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Instala dependências do sistema necessárias para o Django/Postgres/SQLite
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Instala as dependências do projeto
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia o restante do código do projeto
COPY . .

# Cria as pastas necessárias e dá permissão (importante para o Volume)
RUN mkdir -p /app/data /app/staticfiles /app/static /app/media
RUN chmod -R 777 /app/data /app/staticfiles /app/static /app/media

# Comando para coletar estáticos, migrar e iniciar o servidor
# Usamos um script ou o comando direto. O comando abaixo é otimizado para produção.
CMD ["sh", "-c", "python manage.py createsuperuser --noinput || true && \
    python manage.py collectstatic --noinput && \
    python manage.py migrate && \
    gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --log-level debug"]