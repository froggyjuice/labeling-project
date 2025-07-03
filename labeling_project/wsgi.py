# WSGI (Web Server Gateway Interface) 설정 파일
# 웹 서버와 Django 애플리케이션을 연결하는 필수 인터페이스
import os
from django.core.wsgi import get_wsgi_application

# Django 설정 모듈 지정 (기본값: labeling_project.settings)
# 프로덕션에서는 환경 변수로 settings_production.py를 지정할 수 있음
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'labeling_project.settings')

# WSGI 애플리케이션 객체 생성
# 웹 서버(nginx, Apache 등)가 이 객체를 호출하여 Django와 통신
application = get_wsgi_application()
