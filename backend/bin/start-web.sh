#!/bin/sh
set -eu

python manage.py check_hosted_config
python manage.py migrate --check
python manage.py collectstatic --noinput
exec gunicorn crm.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers "${WEB_CONCURRENCY:-2}" \
    --threads "${WEB_THREADS:-2}" \
    --timeout 60 --graceful-timeout 30 \
    --access-logfile - --error-logfile - \
    --access-logformat '%(h)s %(m)s %(U)s %(s)s %(L)s'
