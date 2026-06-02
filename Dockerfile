FROM rockylinux/rockylinux:10

ARG APP_VERSION=dev

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=chronica.settings \
    APP_VERSION=${APP_VERSION} \
    DJANGO_CACHE_DIR=/data/django_cache \
    DJANGO_LOG_DIR=/data \
    NEWS_REFRESH_SECONDS=1200 \
    NEWS_FETCH_LIMIT=30 \
    CATEGORY_FETCH_LIMIT=2 \
    PORT=8000 \
    POSTGRES_HOST=localhost \
    POSTGRES_DB=televideo \
    POSTGRES_USER=televideo \
    PGDATA=/data/postgresql \
    PATH=/usr/pgsql-18/bin:/app:$PATH

WORKDIR /app

RUN dnf -y install --nogpgcheck https://download.postgresql.org/pub/repos/yum/reporpms/EL-10-x86_64/pgdg-redhat-repo-latest.noarch.rpm \
    && rpm --import /etc/pki/rpm-gpg/PGDG-RPM-GPG-KEY-RHEL \
    && dnf -y install python3-pip python3-devel gcc postgresql18-server glibc-langpack-en curl \
    && dnf clean all \
    && ln -sf python3 /usr/bin/python

RUN useradd -m -u 1000 chronica \
    && mkdir -p /data \
    && chown -R chronica:chronica /data

COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x /app/televideo /app/docker/entrypoint.sh /app/docker/force_refresh_meteo.sh /app/docker/migrate_to_postgresql.sh \
    && ln -s /app/docker/force_refresh_meteo.sh /usr/local/bin/refresh-meteo \
    && ln -s /app/docker/migrate_to_postgresql.sh /usr/local/bin/migrate-to-postgresql \
    && DJANGO_SECRET_KEY=build-collectstatic-key python3 web/manage.py collectstatic --noinput

VOLUME ["/data"]
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python3 -c "import urllib.request; req=urllib.request.Request('http://127.0.0.1:8000/healthz/', headers={'X-Forwarded-Proto': 'https'}); urllib.request.urlopen(req, timeout=4).read()"

USER chronica

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["web"]
