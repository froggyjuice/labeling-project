"""
프로덕션 환경용 Django 설정
HTTPS 강제 및 보안 강화
"""

from .settings import *
import os

# 프로덕션용 INSTALLED_APPS (개발용 패키지 제외)
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # 'django_extensions',  # 개발용 - 프로덕션에서 제거
    # 'sslserver',  # 개발용 HTTPS - 프로덕션에서 제거 (Render에서 자동 HTTPS 제공)
    'labeling',
    'storages',  # S3 스토리지용
]

# 프로덕션 환경 설정
DEBUG = False
ALLOWED_HOSTS = [
    'your-domain.com',
    'www.your-domain.com',
    '.onrender.com',  # Render 도메인 허용
    os.environ.get('RENDER_EXTERNAL_HOSTNAME', ''),  # Render 호스트명
]

# CSRF 보안 설정 (Render 도메인 허용)
CSRF_TRUSTED_ORIGINS = [
    'https://*.onrender.com',
    f'https://{os.environ.get("RENDER_EXTERNAL_HOSTNAME", "")}',
]

# HTTPS 강제 설정
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# HSTS (HTTP Strict Transport Security) 설정
SECURE_HSTS_SECONDS = 31536000  # 1년
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# 쿠키 보안 강화
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

# 추가 보안 헤더
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# Content Security Policy (CSP)
CSP_DEFAULT_SRC = ["'self'"]
CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "https://apis.google.com"]
CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"]
CSP_FONT_SRC = ["'self'", "https://fonts.gstatic.com"]
CSP_IMG_SRC = ["'self'", "data:", "https:", "blob:"]
CSP_CONNECT_SRC = ["'self'", "https://accounts.google.com", "https://oauth2.googleapis.com"]

# 데이터베이스 설정 (Render PostgreSQL)
import dj_database_url

# DATABASE_URL이 있으면 사용, 없으면 개별 환경 변수 사용
DATABASES = {
    'default': dj_database_url.config(
        default=f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ.get('DB_PASSWORD', '')}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'labeling_project')}",
        conn_max_age=600,
        conn_health_checks=True,
    )
}

# 로깅 설정 (Render 호환)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'labeling': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# 정적 파일 설정 (프로덕션)
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# WhiteNoise 설정 (정적 파일 서빙)
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # 정적 파일 서빙
] + MIDDLEWARE[1:]  # 기본 미들웨어 유지

# 정적 파일 압축
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# AWS S3 설정 (미디어 파일용)
if os.environ.get('USE_S3') == 'TRUE':
    # S3 설정
    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-northeast-2')  # 서울 리전
    AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
    AWS_DEFAULT_ACL = None
    AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    
    # 미디어 파일 설정
    DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
    MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
else:
    # 로컬 스토리지 (개발/테스트용)
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
    MEDIA_URL = '/media/'

# 캐시 설정 (프로덕션에서는 데이터베이스 사용)
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'django_cache_table',
    }
}

# 세션 스토리지를 데이터베이스로 변경 (Render 호환)
SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2주

# 이메일 설정 (오류 알림용)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# 관리자 알림
ADMINS = [
    ('Admin', os.environ.get('ADMIN_EMAIL', 'admin@your-domain.com')),
]
MANAGERS = ADMINS

# 보안 키 설정 (환경 변수에서 가져오기)
SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY 환경 변수가 설정되지 않았습니다.")

# Google OAuth 설정 (환경 변수에서 가져오기)
GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')

if not GOOGLE_OAUTH_CLIENT_ID or not GOOGLE_OAUTH_CLIENT_SECRET:
    raise ValueError("Google OAuth 환경 변수가 설정되지 않았습니다.")

# Rate Limiting (django-ratelimit 사용시)
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_ENABLE = True

print("🔒 프로덕션 HTTPS 설정이 로드되었습니다.") 