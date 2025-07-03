"""
프로덕션 환경용 Django 설정
HTTPS 강제 및 보안 강화
실제 서비스 운영을 위한 최적화된 설정
"""

from .settings import *
import os

# ===== 필수 설정 (기능 동작에 필수) =====
# 프로덕션용 INSTALLED_APPS (개발용 패키지 제거는 필수)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django_extensions',  # 개발용 - 프로덕션에서 제거 (보안상 불필요한 기능 제거)
    # 'sslserver',  # 개발용 HTTPS - 프로덕션에서 제거 (Render에서 자동 HTTPS 제공)
    'labeling',
    'storages',  # S3 스토리지용 (대용량 파일 저장)
]

# 필수: 프로덕션 환경 설정
DEBUG = False  # 디버그 모드 비활성화 (보안 및 성능 향상)
ALLOWED_HOSTS = [
    'your-domain.com',
    'www.your-domain.com',
    '.onrender.com',  # Render 도메인 허용 (배포 플랫폼)
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''),  # Render 호스트명 (동적 할당)
]

# 필수: CSRF 보안 설정 (Render 도메인 허용)
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    f'https://{os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")}',
]

# CSRF 쿠키 설정 (프로덕션 환경용)
CSRF_COOKIE_SECURE = True  # HTTPS에서만 CSRF 쿠키 전송
CSRF_COOKIE_HTTPONLY = False  # JavaScript에서 CSRF 토큰 접근 허용
CSRF_COOKIE_SAMESITE = 'Lax'  # CSRF 쿠키의 SameSite 속성
CSRF_USE_SESSIONS = False  # 세션 대신 쿠키 사용
CSRF_COOKIE_AGE = 31449600  # CSRF 쿠키 만료 시간 (1년)

# 프록시 헤더 설정 (Render 환경)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True
USE_X_FORWARDED_PORT = True
# 필수: 데이터베이스 설정 (Render PostgreSQL)
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ.get('DB_PASSWORD', '')}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'labeling_project')}",
        conn_max_age=600,  # 연결 유지 시간 (10분)
        conn_health_checks=True,  # 연결 상태 확인
    )
}


# 필수: 정적 파일 설정 (프로덕션)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 필수: 보안 키 설정 (환경 변수에서 가져오기 또는 임시 키)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY', 'django-insecure-temp-key-for-initial-deploy-change-this-immediately-123456789')
if SECRET_KEY == 'django-insecure-temp-key-for-initial-deploy-change-this-immediately-123456789':
    print("⚠️  경고: 임시 SECRET_KEY 사용 중! 환경 변수를 설정하세요.")

# 필수: Google IAM 서비스 계정 설정 (환경 변수에서 가져오기)
GOOGLE_SERVICE_ACCOUNT_KEY_PATH = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_PATH', 'image-labeling-test-464107-ae81484b9900.json')
GOOGLE_SERVICE_ACCOUNT_KEY_JSON = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_JSON', '')

if not GOOGLE_SERVICE_ACCOUNT_KEY_JSON:
    print("⚠️  경고: GOOGLE_SERVICE_ACCOUNT_KEY_JSON 환경 변수가 설정되지 않았습니다. Google Drive 접근이 작동하지 않을 수 있습니다.")

# 필수: 세션 및 쿠키 보안 설정 (HTTPS 환경)
SESSION_COOKIE_SECURE = True  # HTTPS에서만 세션 쿠키 전송
SESSION_COOKIE_HTTPONLY = True  # JavaScript에서 세션 쿠키 접근 차단
SESSION_COOKIE_SAMESITE = 'Lax'  # 세션 쿠키의 SameSite 속성
SESSION_COOKIE_AGE = 86400  # 24시간 (초 단위)
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

print("🔒 프로덕션 HTTPS 설정이 로드되었습니다.") 
