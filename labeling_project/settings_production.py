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

# 필수: 데이터베이스 설정 (Render PostgreSQL)
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ.get('DB_PASSWORD', '')}@{os.environ.get('DB_HOST', 'localhost')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'labeling_project')}",
        conn_max_age=600,  # 연결 유지 시간 (10분)
        conn_health_checks=True,  # 연결 상태 확인
        options={
            'MAX_CONNS': 20,  # 최대 연결 수
            'MIN_CONNS': 5,   # 최소 연결 수
        }
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

# ===== 선택적 설정 (성능/보안 최적화) =====
# # 선택: HTTPS 강제 설정 (모든 HTTP 요청을 HTTPS로 리다이렉트)
# SECURE_SSL_REDIRECT = True
# SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# # 선택: HSTS (HTTP Strict Transport Security) 설정 (브라우저가 HTTPS만 사용하도록 강제)
# SECURE_HSTS_SECONDS = 31536000  # 1년
# SECURE_HSTS_INCLUDE_SUBDOMAINS = True
# SECURE_HSTS_PRELOAD = True

# # 선택: 쿠키 보안 강화 (HTTPS에서만 전송, JavaScript 접근 차단)
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True
# SESSION_COOKIE_HTTPONLY = True
# CSRF_COOKIE_HTTPONLY = True

# # 선택: 추가 보안 헤더 (XSS, 클릭재킹 등 공격 방지)
# SECURE_BROWSER_XSS_FILTER = True
# SECURE_CONTENT_TYPE_NOSNIFF = True
# X_FRAME_OPTIONS = 'DENY'
# SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# # 선택: Content Security Policy (CSP) - 리소스 로딩 제한
# CSP_DEFAULT_SRC = ["'self'"]
# CSP_SCRIPT_SRC = ["'self'", "'unsafe-inline'", "https://apis.google.com"]
# CSP_STYLE_SRC = ["'self'", "'unsafe-inline'", "https://fonts.googleapis.com"]
# CSP_FONT_SRC = ["'self'", "https://fonts.gstatic.com"]
# CSP_IMG_SRC = ["'self'", "data:", "https:", "blob:"]
# CSP_CONNECT_SRC = ["'self'", "https://accounts.google.com", "https://oauth2.googleapis.com"]

# # 선택: 데이터베이스 최적화 설정
# DATABASE_OPTIONS = {
#     'OPTIONS': {
#         'MAX_CONNS': 20,
#         'MIN_CONNS': 5,
#         'CONN_MAX_AGE': 600,
#         'CONN_HEALTH_CHECKS': True,
#     }
# }

# # 선택: 로깅 설정 (Render 호환) - 서비스 모니터링 및 오류 추적
# LOGGING = {
#     'version': 1,
#     'disable_existing_loggers': False,
#     'formatters': {
#         'verbose': {
#             'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
#             'style': '{',
#         },
#         'simple': {
#             'format': '{levelname} {message}',
#             'style': '{',
#         },
#     },
#     'handlers': {
#         'console': {
#             'level': 'WARNING',  # INFO에서 WARNING으로 변경하여 로그 양 감소 (성능 최적화)
#             'class': 'logging.StreamHandler',
#             'formatter': 'verbose',
#         },
#     },
#     'root': {
#         'handlers': ['console'],
#         'level': 'WARNING',  # INFO에서 WARNING으로 변경
#     },
#     'loggers': {
#         'django': {
#             'handlers': ['console'],
#             'level': 'WARNING',  # INFO에서 WARNING으로 변경
#             'propagate': False,
#         },
#         'labeling': {
#             'handlers': ['console'],
#             'level': 'WARNING',  # INFO에서 WARNING으로 변경
#             'propagate': False,
#         },
#         'django.db.backends': {
#             'handlers': ['console'],
#             'level': 'ERROR',  # SQL 쿼리 로그 비활성화 (성능 향상)
#             'propagate': False,
#         },
#     },
# }

# # 선택: WhiteNoise 설정 (정적 파일 서빙) - CDN 없이도 빠른 정적 파일 제공
# MIDDLEWARE = [
#     'django.middleware.security.SecurityMiddleware',
#     'whitenoise.middleware.WhiteNoiseMiddleware',  # 정적 파일 서빙
# ] + MIDDLEWARE[1:]  # 기본 미들웨어 유지

# # 선택: 정적 파일 압축 및 캐싱 최적화
# STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# # 선택: WhiteNoise 추가 설정
# WHITENOISE_USE_FINDERS = True
# WHITENOISE_AUTOREFRESH = True
# WHITENOISE_MAX_AGE = 31536000  # 1년 캐시

# # 선택: 템플릿 캐싱 활성화 (성능 향상)
# TEMPLATES[0]['OPTIONS']['loaders'] = [
#     ('django.template.loaders.cached.Loader', [
#         'django.template.loaders.filesystem.Loader',
#         'django.template.loaders.app_directories.Loader',
#     ]),
# ]

# # 선택: AWS S3 설정 (미디어 파일용) - 대용량 이미지 파일 저장
# if os.environ.get('USE_S3') == 'TRUE':
#     # S3 설정
#     AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID')
#     AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY')
#     AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME')
#     AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'ap-northeast-2')  # 서울 리전
#     AWS_S3_CUSTOM_DOMAIN = f'{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com'
#     AWS_DEFAULT_ACL = None
#     AWS_S3_OBJECT_PARAMETERS = {'CacheControl': 'max-age=86400'}
    
#     # 미디어 파일 설정
#     DEFAULT_FILE_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'
#     MEDIA_URL = f'https://{AWS_S3_CUSTOM_DOMAIN}/'
# else:
#     # 로컬 스토리지 (개발/테스트용)
#     MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
#     MEDIA_URL = '/media/'

# # 선택: 캐시 설정 (프로덕션에서는 데이터베이스 사용) - 성능 최적화
# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
#         'LOCATION': 'django_cache_table',
#         'TIMEOUT': 300,  # 5분 캐시
#         'OPTIONS': {
#             'MAX_ENTRIES': 1000,
#         }
#     }
# }

# # 선택: 세션 스토리지를 데이터베이스로 변경 (Render 호환) - 다중 서버 환경 지원
# SESSION_ENGINE = 'django.contrib.sessions.backends.db'
# SESSION_COOKIE_AGE = 1209600  # 2주

# # 선택: 이메일 설정 (오류 알림용) - 서비스 모니터링
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = os.environ.get('EMAIL_HOST', 'smtp.gmail.com')
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')

# # 선택: 관리자 알림
# ADMINS = [
#     ('Admin', os.environ.get('ADMIN_EMAIL', 'admin@your-domain.com')),
# ]
# MANAGERS = ADMINS

# # 선택: Rate Limiting (django-ratelimit 사용시) - DDoS 공격 방지
# RATELIMIT_USE_CACHE = 'default'
# RATELIMIT_ENABLE = True

print("🔒 프로덕션 HTTPS 설정이 로드되었습니다.") 