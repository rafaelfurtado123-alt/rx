# Néfron API — imagem de produção (usada no docker-compose do deploy)
FROM python:3.12-slim

# Dependências nativas mínimas (reportlab/Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
        libjpeg62-turbo zlib1g && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /srv/backend

# Instala primeiro as dependências (cache de camada)
COPY pyproject.toml README.md ./
COPY app ./app
COPY scripts ./scripts
RUN pip install --no-cache-dir .

EXPOSE 8000

# Usuário não-root
RUN useradd -r -u 10001 nefron
USER nefron

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
