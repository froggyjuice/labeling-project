@echo off
echo ========================================
echo    Django + ngrok HTTPS 호스팅 시작
echo ========================================

REM 현재 디렉토리 확인
echo 현재 디렉토리: %CD%

REM 가상환경 활성화 확인
echo 가상환경 확인 중...
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo 오류: Python이 설치되지 않았거나 PATH에 없습니다.
    pause
    exit /b 1
)

REM Django 의존성 확인
echo Django 설치 확인 중...
python -c "import django" >nul 2>&1
if %errorlevel% neq 0 (
    echo Django가 설치되지 않았습니다. 설치 중...
    pip install -r requirements.txt
)

REM ngrok 설치 확인
echo ngrok 설치 확인 중...
if exist "ngrok\ngrok.exe" (
    echo ngrok 발견: ngrok\ngrok.exe
) else (
    echo 오류: ngrok.exe를 찾을 수 없습니다!
    echo ngrok.zip이 있다면 먼저 압축을 풀어주세요.
    echo 또는 다음 링크에서 ngrok을 다운로드하세요: https://ngrok.com/download
    echo 또는 Chocolatey로 설치: choco install ngrok
    pause
    exit /b 1
)

REM 환경변수 파일 확인
if not exist ".env" (
    echo 경고: .env 파일이 없습니다.
    echo Google OAuth 설정을 위해 .env 파일을 만들어주세요.
    echo 예시:
    echo GOOGLE_CLIENT_ID=your_client_id
    echo GOOGLE_CLIENT_SECRET=your_client_secret
    echo.
)

REM 정적 파일 수집
echo 정적 파일 수집 중...
python manage.py collectstatic --noinput

REM 데이터베이스 마이그레이션 확인
echo 데이터베이스 마이그레이션 확인 중...
python manage.py migrate

echo.
echo ========================================
echo Django 서버와 ngrok 터널을 시작합니다...
echo ========================================
echo.

REM 새 터미널에서 Django 서버 실행
echo Django 서버 시작 중 (포트 8000)...
start "Django Server" cmd /k "python manage.py runserver 8000"

REM 3초 대기 후 ngrok 실행
echo 3초 후 ngrok 터널을 시작합니다...
timeout /t 3 /nobreak >nul

echo ngrok HTTPS 터널 시작 중...
echo.
echo ========================================
echo    중요: 아래 HTTPS URL을 사용하세요!
echo ========================================

REM ngrok 터널 시작 (현재 터미널에서)
ngrok\ngrok.exe http 8000

echo.
echo ngrok이 종료되었습니다.
echo Django 서버도 종료하려면 Django Server 창을 닫아주세요.
pause 