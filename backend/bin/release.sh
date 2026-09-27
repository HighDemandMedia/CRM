#!/bin/sh
set -eu

# Configure this as the API's Render Pre-Deploy Command, once per release.
python manage.py check_hosted_config
python manage.py migrate --noinput
python manage.py check
