#!/usr/bin/env bash
# build.sh

set -o errexit  # exit on error

pip install -r requirements.txt

# Django 설정
python manage.py collectstatic --no-input
python manage.py migrate 