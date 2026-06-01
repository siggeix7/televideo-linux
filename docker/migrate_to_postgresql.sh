#!/bin/sh
set -eu
cd /app
exec python web/manage.py migrate_to_postgresql
