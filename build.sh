#!/usr/bin/env bash
# build.sh

set -o errexit  # exit on error

pip install -r requirements.txt

# Django 설정
python manage.py collectstatic --no-input
python manage.py migrate

# 캐시 테이블 생성 (데이터베이스 캐시용)
python manage.py createcachetable 