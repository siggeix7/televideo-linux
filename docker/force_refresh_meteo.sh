#!/bin/sh
set -eu
cd /app
exec python web/manage.py force_refresh_meteo
