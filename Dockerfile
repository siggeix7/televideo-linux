FROM python:3.12-slim

ARG APP_VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=chronica.settings \
    APP_VERSION=${APP_VERSION} \
    SQLITE_PATH=/data/chronica.sqlite3 \
    DJANGO_CACHE_DIR=/data/django_cache \
    DJANGO_LOG_DIR=/data \
    NEWS_REFRESH_SECONDS=1800 \
    NEWS_FETCH_LIMIT=30 \
    CATEGORY_FETCH_LIMIT=2 \
    PORT=8000 \
    PGDATA=/data/postgresql \
    PATH=/usr/lib/postgresql/18/bin:/app:$PATH

WORKDIR /app

RUN apt-get update && apt-get install -y curl ca-certificates gnupg && \
    curl -fsSL https://www.postgresql.org/media/keys/ACCC4CF8.asc | gpg --dearmor -o /usr/share/keyrings/postgresql.gpg && \
    echo "deb [signed-by=/usr/share/keyrings/postgresql.gpg] http://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" > /etc/apt/sources.list.d/pgdg.list && \
    apt-get update && apt-get install -y postgresql-18 && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

RUN adduser --disabled-password --gecos "" chronica \
    && mkdir -p /data \
    && chown -R chronica:chronica /data

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/televideo /app/docker/entrypoint.sh /app/docker/force_refresh_meteo.sh /app/docker/migrate_to_postgresql.sh \
    && ln -s /app/docker/force_refresh_meteo.sh /usr/local/bin/refresh-meteo \
    && ln -s /app/docker/migrate_to_postgresql.sh /usr/local/bin/migrate-to-postgresql \
    && python web/manage.py collectstatic --noinput

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8000/healthz/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(req, timeout=4).read()"

USER chronica

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
