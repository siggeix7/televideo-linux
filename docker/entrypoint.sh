#!/bin/sh
set -eu

cd /app

if [ "${1:-web}" = "manage" ]; then
    shift
    exec python web/manage.py "$@"
fi

if [ "${1:-web}" = "worker" ]; then
    exec python web/manage.py fetch_televideo --loop --interval "${NEWS_REFRESH_SECONDS:-60}" --limit "${NEWS_FETCH_LIMIT:-12}" --category-limit "${CATEGORY_FETCH_LIMIT:-2}"
fi

if [ "${1:-web}" != "web" ]; then
    exec "$@"
fi

python web/manage.py showmigrations --plan >/dev/null
python web/manage.py migrate --noinput

# Background worker: news, lotto, superenalotto
python web/manage.py fetch_televideo --loop --interval "${NEWS_REFRESH_SECONDS:-60}" --limit "${NEWS_FETCH_LIMIT:-12}" --category-limit "${CATEGORY_FETCH_LIMIT:-2}" &

# Background worker: section snapshots (TV, sport, cultura, etc.)
python web/manage.py fetch_sections --loop --interval "${TELETEXT_SECTION_REFRESH_SECONDS:-1800}" &

exec gunicorn chronica.wsgi:application \
    --chdir web \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --timeout "${WEB_TIMEOUT:-90}"
