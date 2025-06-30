# 🚀 Render 배포 가이드

## 1단계: GitHub 리포지토리 설정

### 1-1. GitHub에 리포지토리 생성
```bash
# Git 초기화 (아직 안했다면)
git init
git add .
git commit -m "Initial commit for Render deployment"

# GitHub 리포지토리 연결
git remote add origin https://github.com/YOUR_USERNAME/labeling-project.git
git branch -M main
git push -u origin main
```

### 1-2. 중요 파일들 확인
- ✅ `requirements.txt` (의존성)
- ✅ `build.sh` (빌드 스크립트)
- ✅ `render.yaml` (Render 설정)
- ✅ `labeling_project/settings_production.py` (프로덕션 설정)

## 2단계: AWS S3 버킷 생성 (미디어 파일용)

### 2-1. AWS 콘솔 로그인
1. https://aws.amazon.com/console/ 접속
2. S3 서비스 선택

### 2-2. S3 버킷 생성
```
버킷 이름: labeling-project-media-YOUR-NAME
리전: Asia Pacific (Seoul) ap-northeast-2
퍼블릭 액세스: 차단 해제 (미디어 파일 접근용)
```

### 2-3. IAM 사용자 생성
1. IAM → 사용자 → 사용자 추가
2. 사용자 이름: `labeling-project-s3-user`
3. 권한: `AmazonS3FullAccess` 정책 연결
4. 액세스 키 생성 → CSV 다운로드 (중요!)

## 3단계: Render 계정 설정

### 3-1. Render 계정 생성
1. https://render.com 접속
2. GitHub 계정으로 가입
3. GitHub 리포지토리 연결 권한 부여

### 3-2. PostgreSQL 데이터베이스 생성
1. Render 대시보드 → New → PostgreSQL
```
Name: labeling-postgres
Database: labeling_project
User: labeling_user
Region: Singapore (가장 가까운 리전)
Plan: Free
```

2. 생성 완료 후 `External Database URL` 복사

### 3-3. Web Service 생성
1. Render 대시보드 → New → Web Service
2. GitHub 리포지토리 선택
3. 다음 설정 입력:

```
Name: labeling-project
Environment: Python 3
Region: Singapore
Branch: main
Build Command: ./build.sh
Start Command: gunicorn labeling_project.wsgi:application
```

## 4단계: 환경 변수 설정

### 4-1. 필수 환경 변수 (Render Web Service → Environment)

#### Django 기본 설정
```
DJANGO_SETTINGS_MODULE=labeling_project.settings_production
DJANGO_SECRET_KEY=[Render에서 Generate 버튼 클릭]
DEBUG=False
```

#### 데이터베이스
```
DATABASE_URL=[3-2에서 복사한 PostgreSQL External Database URL]
```

#### Google OAuth
```
GOOGLE_CLIENT_ID=[현재 api_key.txt의 client_id 값]
GOOGLE_CLIENT_SECRET=[현재 api_key.txt의 client_secret 값]  
```

#### AWS S3 (미디어 파일)
```
USE_S3=TRUE
AWS_ACCESS_KEY_ID=[2-3에서 생성한 액세스 키]
AWS_SECRET_ACCESS_KEY=[2-3에서 생성한 시크릿 키]
AWS_STORAGE_BUCKET_NAME=[2-2에서 생성한 버킷 이름]
AWS_S3_REGION_NAME=ap-northeast-2
```

#### 선택사항 (이메일 알림)
```
EMAIL_HOST=smtp.gmail.com
EMAIL_HOST_USER=[Gmail 주소]
EMAIL_HOST_PASSWORD=[Gmail 앱 비밀번호]
ADMIN_EMAIL=[관리자 이메일]
```

### 4-2. 환경 변수 저장 후 배포 대기

## 5단계: 도메인 및 Google OAuth 업데이트

### 5-1. Render 도메인 확인
배포 완료 후 `https://your-app-name.onrender.com` 형태의 URL 획득

### 5-2. Google OAuth 콘솔 업데이트
1. https://console.developers.google.com 접속
2. 프로젝트 선택 → API 및 서비스 → OAuth 2.0 클라이언트 ID
3. 승인된 리디렉션 URI에 추가:
```
https://your-app-name.onrender.com/google-user-auth-callback/
https://your-app-name.onrender.com/google-admin-auth-callback/
https://your-app-name.onrender.com/google-drive-auth-callback/
```

## 6단계: 데이터 마이그레이션

### 6-1. 기존 미디어 파일 S3 업로드
```bash
# AWS CLI 설치 후
aws configure  # Access Key 입력
aws s3 sync ./media/ s3://your-bucket-name/ --recursive
```

### 6-2. 데이터베이스 데이터 이동 (필요시)
```bash
# 로컬 데이터 백업
python manage.py dumpdata > backup.json

# Render에서 복원 (Render Shell 이용)
python manage.py loaddata backup.json
```

## 7단계: 배포 확인

### 7-1. 서비스 상태 확인
- Render 대시보드에서 배포 로그 확인
- 에러 없이 "Deploy succeeded" 메시지 확인

### 7-2. 웹사이트 접속 테스트
1. `https://your-app-name.onrender.com` 접속
2. Google 로그인 테스트
3. 이미지 업로드/표시 테스트
4. 관리자 대시보드 테스트

## 8단계: 도메인 연결 (선택사항)

### 8-1. 커스텀 도메인 설정
1. Render → Settings → Custom Domains
2. 도메인 추가 (예: labeling.your-domain.com)
3. DNS 설정에 CNAME 레코드 추가

## 🎉 배포 완료!

팀원들이 24시간 접근 가능한 서비스가 준비되었습니다.

## 📊 모니터링 및 유지보수

### Render 무료 플랜 주의사항
- 15분 비활성 시 슬립 모드 (첫 접속 시 30초 로딩)
- 월 750시간 제한 (유료 플랜 고려)

### 업데이트 방법
```bash
git add .
git commit -m "Update message"
git push origin main
# Render에서 자동 재배포
```

### 백업 권장사항
- 정기적인 데이터베이스 백업
- S3 버킷 버전 관리 활성화
- 환경 변수 별도 기록 보관 