#!/bin/sh
set -eu

cd /app

if [ "${1:-web}" = "manage" ]; then
    shift
    exec python web/manage.py "$@"
fi

if [ "${1:-web}" = "worker" ]; then
    exec python web/manage.py fetch_televideo --loop --interval "${NEWS_REFRESH_SECONDS:-1800}" --limit "${NEWS_FETCH_LIMIT:-30}" --category-limit "${CATEGORY_FETCH_LIMIT:-2}"
fi

if [ "${1:-web}" != "web" ]; then
    exec "$@"
fi

# Start embedded PostgreSQL if configured
if [ -n "${POSTGRES_HOST:-}" ] && [ "${POSTGRES_HOST}" = "localhost" ]; then
    PGDATA="${PGDATA:-/data/postgresql}"
    PGUSER="${POSTGRES_USER:-televideo}"
    PGPASSWORD="${POSTGRES_PASSWORD:-}"
    PGHOST="/data"
    export PGPASSWORD

    PG_AUTH_FILE="$PGDATA/pg_hba.conf"

    if ! pg_isready -q -h "$PGHOST" 2>/dev/null; then
        if [ ! -f "$PGDATA/PG_VERSION" ]; then
            echo "Initialising PostgreSQL data directory at $PGDATA ..."
            initdb -D "$PGDATA" --locale=C.UTF-8 --encoding=UTF8 --username="$PGUSER" --auth=trust
        fi

        # Harden auth: ensure pg_hba.conf uses scram-sha-256 after password is set
        if grep -q 'trust$' "$PG_AUTH_FILE" 2>/dev/null; then
            if [ -n "$PGPASSWORD" ]; then
                echo "Starting PostgreSQL (setup mode) ..."
                pg_ctl -D "$PGDATA" -o "-k $PGHOST -c listen_addresses=" -l /data/postgresql.log start
                until pg_isready -q -h "$PGHOST" 2>/dev/null; do sleep 1; done
                echo "Setting password for $PGUSER ..."
                ESCAPED_PW=$(printf '%s' "$PGPASSWORD" | sed "s/'/''/g")
                psql -h "$PGHOST" -U "$PGUSER" -d postgres -c "ALTER ROLE \"$PGUSER\" PASSWORD '${ESCAPED_PW}'" >/dev/null
                pg_ctl -D "$PGDATA" stop -m fast 2>/dev/null || true
                sed -i 's/trust$/scram-sha-256/' "$PG_AUTH_FILE"
                echo "PostgreSQL auth hardened to scram-sha-256."
            else
                echo "WARNING: POSTGRES_PASSWORD not set. PostgreSQL will use trust authentication (insecure)." >&2
            fi
        fi

        echo "Starting PostgreSQL ..."
        pg_ctl -D "$PGDATA" -o "-k $PGHOST" -l /data/postgresql.log start
        until pg_isready -q -h "$PGHOST" 2>/dev/null; do
            sleep 1
        done
    fi
    if ! psql -h "$PGHOST" -U "$PGUSER" -lqt 2>/dev/null | cut -d '|' -f 1 | grep -qw "${POSTGRES_DB:-televideo}"; then
        createdb -h "$PGHOST" -U "$PGUSER" "${POSTGRES_DB:-televideo}"
    fi
    echo "PostgreSQL is ready."
fi

python web/manage.py showmigrations --plan >/dev/null
python web/manage.py migrate --noinput --database=default

rm -rf "${DJANGO_CACHE_DIR:-/data/django_cache}"/*
mkdir -p "${DJANGO_CACHE_DIR:-/data/django_cache}"

# Background worker: news, lotto, superenalotto
python web/manage.py fetch_televideo --loop --interval "${NEWS_REFRESH_SECONDS:-1800}" --limit "${NEWS_FETCH_LIMIT:-30}" --category-limit "${CATEGORY_FETCH_LIMIT:-2}" &

# Background worker: section snapshots (TV, sport, cultura, etc.)
python web/manage.py fetch_sections --loop --interval "${TELETEXT_SECTION_REFRESH_SECONDS:-1800}" &

# Optional OpenWeatherMap fallback for missing province-capital weather.
if [ -n "${OPENWEATHER_API_KEY:-}" ]; then
    python web/manage.py refresh_openweather --loop --interval "${OPENWEATHER_REFRESH_CHECK_SECONDS:-9000}" &
fi

exec gunicorn chronica.wsgi:application \
    --chdir web \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${WEB_TIMEOUT:-90}"
