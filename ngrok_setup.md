# 🌐 ngrok HTTPS 호스팅 가이드

팀원과 공유할 수 있도록 Django 이미지 라벨링 시스템을 ngrok을 통해 HTTPS로 호스팅하는 방법입니다.

## 1. ngrok 설치

### ✅ 로컬 설치 (권장 - 이미 완료!):
프로젝트에 `ngrok.exe`가 이미 준비되어 있습니다! 관리자 권한이 필요하지 않습니다.

```bash
# 이미 완료됨: ngrok/ngrok.exe 파일이 존재함
# 만약 ngrok.zip만 있다면 압축 해제:
Expand-Archive ngrok.zip
```

### 대안 설치 방법들:

#### Chocolatey (관리자 권한 필요):
```bash
# 관리자 권한 PowerShell에서
choco install ngrok
```

#### 수동 다운로드:
```bash
# https://ngrok.com/download 에서 Windows 버전 다운로드
# 압축 해제 후 PATH에 추가하거나 프로젝트 폴더에 저장
```

#### PowerShell 직접 다운로드:
```bash
Invoke-WebRequest -Uri "https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-amd64.zip" -OutFile "ngrok.zip"
Expand-Archive ngrok.zip
# System32로 이동 대신 로컬에서 사용하는 것을 권장
```

## 2. ngrok 계정 설정 (권장)

1. https://ngrok.com 에서 무료 계정 생성
2. 인증 토큰 설정:
```bash
ngrok authtoken YOUR_AUTH_TOKEN
```

## 3. Django 설정 확인

✅ **이미 완료된 설정들:**
- `ALLOWED_HOSTS`에 ngrok 도메인 추가됨
- `CSRF_TRUSTED_ORIGINS` 설정됨
- Google OAuth 리디렉션 URI 동적 처리
- HTTPS 프록시 헤더 설정

## 4. 환경 변수 설정

`.env` 파일이 있는지 확인하고 Google OAuth 설정:

```bash
# .env 파일 내용
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
```

## 5. 정적 파일 수집

```bash
python manage.py collectstatic --noinput
```

## 6. 빠른 시작 🚀

### ⚡ 원클릭 실행 (권장):
```powershell
# PowerShell에서 실행
.\start_ngrok.ps1

# 또는 배치 파일
.\start_ngrok.bat
```

### 수동 실행:
```bash
# 터미널 1: Django 서버 실행
python manage.py runserver 8000

# 터미널 2: ngrok 터널 실행 (로컬 파일 사용)
.\ngrok\ngrok.exe http 8000

# 또는 시스템에 설치된 경우
ngrok http 8000
```

### 고급 옵션:
```bash
# 사용자 정의 도메인 (Pro 계정)
.\ngrok\ngrok.exe http 8000 --subdomain=your-project-name

# 로그 레벨 조정
.\ngrok\ngrok.exe http 8000 --log=stdout --log-level=debug
```

## 7. Google Cloud Console 설정 업데이트

ngrok이 실행되면 다음과 같은 HTTPS URL을 받게 됩니다:
```
https://abcd1234.ngrok-free.app
```

이 URL을 Google Cloud Console에 추가:

1. [Google Cloud Console](https://console.cloud.google.com) → OAuth 2.0 클라이언트 ID
2. **승인된 JavaScript 출처**에 추가:
   - `https://your-ngrok-url.ngrok-free.app`
3. **승인된 리디렉션 URI**에 추가:
   - `https://your-ngrok-url.ngrok-free.app/google-user-auth-callback/`
   - `https://your-ngrok-url.ngrok-free.app/google-admin-auth-callback/`
   - `https://your-ngrok-url.ngrok-free.app/google-drive-auth-callback/`

## 8. 팀원 공유

ngrok URL을 팀원에게 공유:
- **일반 사용자**: `https://your-ngrok-url.ngrok-free.app/user-login/`
- **관리자**: `https://your-ngrok-url.ngrok-free.app/admin-login/`

## 9. 보안 고려사항

✅ **이미 구현된 보안 기능:**
- CSRF 보호
- 사용자 승인 시스템
- 역할 기반 접근 제어
- 이미지 접근 로깅
- Rate limiting

🔒 **추가 권장사항:**
- ngrok 무료 버전은 8시간 제한이 있음
- 프로덕션에서는 유료 ngrok 또는 실제 서버 사용 권장
- `.env` 파일은 절대 git에 커밋하지 말 것

## 10. 문제 해결

### ngrok 재시작 시 URL 변경 문제:
- 무료 계정은 재시작마다 URL이 변경됨
- Google OAuth 설정도 매번 업데이트 필요
- 해결: ngrok Pro 계정으로 고정 도메인 사용

### 이미지가 안 보이는 경우:
1. 관리자로 로그인 후 Google Drive 권한 설정 확인
2. 관리자 대시보드에서 "Google Drive 권한으로 다시 로그인" 클릭

### CORS 오류:
- `CSRF_TRUSTED_ORIGINS`에 새 ngrok URL 추가
- Django 서버 재시작

## 11. 프로덕션 배포 (선택사항)

실제 프로덕션 환경에서는:
- Heroku, DigitalOcean, AWS 등 사용
- 고정 도메인 및 SSL 인증서
- 데이터베이스를 PostgreSQL로 변경
- 정적 파일을 CDN으로 서빙 