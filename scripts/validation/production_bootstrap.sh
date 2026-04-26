#!/usr/bin/env bash
set -euo pipefail

echo "[v40] checking Django deployment settings"
python manage.py check --deploy

echo "[v40] checking pending migrations"
python manage.py makemigrations --check --dry-run

echo "[v40] applying migrations"
python manage.py migrate --noinput

echo "[v40] collecting static files"
python manage.py collectstatic --noinput

echo "[v40] running production preflight"
python manage.py ops_production_preflight --json
