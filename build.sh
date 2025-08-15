#!/usr/bin/env bash
# exit on error
set -o errexit  

pip install -r requirements.txt

# Collect static files
python manage.py collectstatic --no-input --clear

# Apply database migrations
python manage.py migrate --no-input
