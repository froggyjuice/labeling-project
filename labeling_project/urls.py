# labeling_project/urls.py - 메인 프로젝트 URL 설정
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# 메인 URL 패턴 정의
urlpatterns = [
    path('admin/', admin.site.urls),  # Django 관리자 인터페이스 (/admin/ 경로)
    path('', include('labeling.urls')),  # labeling 앱의 URL들을 루트 경로에 포함
]

# 개발 환경에서 미디어 파일 서빙 설정
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # 업로드된 파일들을 개발 서버에서 직접 서빙