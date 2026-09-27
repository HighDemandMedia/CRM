#!/bin/sh
set -eu

python manage.py check_hosted_config
python manage.py migrate --check
# Exactly one scheduler instance. Its schedule file is disposable.
exec celery -A crm beat --loglevel=info --schedule=/tmp/crm-celerybeat
