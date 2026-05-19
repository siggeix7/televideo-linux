FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=chronica.settings \
    SQLITE_PATH=/data/chronica.sqlite3 \
    NEWS_REFRESH_SECONDS=60 \
    NEWS_FETCH_LIMIT=12 \
    CATEGORY_FETCH_LIMIT=2 \
    PORT=8000

WORKDIR /app

RUN adduser --disabled-password --gecos "" chronica \
    && mkdir -p /data \
    && chown -R chronica:chronica /data

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/televideo /app/docker/entrypoint.sh \
    && python web/manage.py collectstatic --noinput

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8000/healthz/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(req, timeout=4).read()"

USER chronica

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
