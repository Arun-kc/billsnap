FROM python:3.12-slim

WORKDIR /app

# Install system deps for Pillow and asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml .
RUN pip install --no-cache-dir -e .

COPY . .

EXPOSE 8000

RUN chmod +x start.sh

CMD ["/bin/sh", "start.sh"]
