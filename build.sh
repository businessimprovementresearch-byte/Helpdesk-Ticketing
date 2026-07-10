#!/usr/bin/env bash
# Build script dipakai oleh Render saat deploy.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
