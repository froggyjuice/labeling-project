#!/usr/bin/env bash
# build.sh

set -o errexit  # exit on error

pip install -r requirements.txt

# Django 설정
python manage.py collectstatic --no-input # 정적 파일 수집
python manage.py migrate # 데이터베이스 마이그레이션

# 캐시 테이블 생성 (데이터베이스 캐시용)
python manage.py createcachetable 