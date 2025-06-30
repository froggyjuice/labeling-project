# Render 환경 변수 설정 가이드

## 필수 환경 변수 (Render 대시보드에 설정)

### Django 기본 설정
- `DJANGO_SETTINGS_MODULE` = `labeling_project.settings_production`
- `DJANGO_SECRET_KEY` = (Render에서 자동 생성하거나 직접 설정)
- `DEBUG` = `False`

### 데이터베이스
- `DATABASE_URL` = (Render PostgreSQL 연결 시 자동 설정)

### Google OAuth (현재 api_key.txt에서 가져올 값)
- `GOOGLE_CLIENT_ID` = (Google OAuth 클라이언트 ID)
- `GOOGLE_CLIENT_SECRET` = (Google OAuth 클라이언트 시크릿)

### 선택적 환경 변수
- `EMAIL_HOST` = `smtp.gmail.com`
- `EMAIL_HOST_USER` = (Gmail 주소)
- `EMAIL_HOST_PASSWORD` = (Gmail 앱 비밀번호)
- `ADMIN_EMAIL` = (관리자 이메일)
- `REDIS_URL` = (Redis 사용 시, Render Redis 애드온에서 자동 설정)

## 설정 방법
1. Render 대시보드 → 서비스 → Environment
2. 위 환경 변수들을 하나씩 추가
3. 저장 후 재배포 