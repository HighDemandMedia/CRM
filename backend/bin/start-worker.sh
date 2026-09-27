#!/bin/sh
set -eu

python manage.py check_hosted_config
python manage.py migrate --check
exec celery -A crm worker --loglevel=info --concurrency="${CELERY_CONCURRENCY:-2}"
