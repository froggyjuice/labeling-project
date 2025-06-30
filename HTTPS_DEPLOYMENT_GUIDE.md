# 🔐 HTTPS 프로덕션 배포 가이드

이 가이드는 Django 이미지 라벨링 프로젝트를 HTTPS로 보안이 강화된 프로덕션 환경에 배포하는 방법을 설명합니다.

## 📋 목차
1. [개발 환경에서 HTTPS 테스트](#개발-환경에서-https-테스트)
2. [프로덕션 환경 구성 요소](#프로덕션-환경-구성-요소)
3. [서버 준비](#서버-준비)
4. [SSL 인증서 획득](#ssl-인증서-획득)
5. [Docker 배포](#docker-배포)
6. [Google OAuth 설정](#google-oauth-설정)
7. [보안 설정 확인](#보안-설정-확인)
8. [모니터링 및 유지보수](#모니터링-및-유지보수)

---

## 🧪 개발 환경에서 HTTPS 테스트

### 1. 필요한 패키지 설치 확인
```bash
pip install django-extensions pyOpenSSL
```

### 2. HTTPS 개발 서버 실행
```bash
python manage.py runserver_plus --cert-file cert.crt --key-file key.key 127.0.0.1:8443
```

### 3. 브라우저에서 접속
- https://127.0.0.1:8443 접속
- 자체 서명 인증서 경고가 나타나면 "고급" → "안전하지 않음(unsafe)으로 계속" 클릭

### 4. OAuth 설정에서 HTTPS 비활성화
HTTPS 사용 시 `labeling/views.py`의 다음 라인을 주석 처리하세요:
```python
# os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # HTTPS 사용시 주석 처리
```

---

## 🏭 프로덕션 환경 구성 요소

### 아키텍처 개요
```
인터넷 → Nginx (SSL 터미네이션) → Django/Gunicorn → PostgreSQL
                    ↓
                  Redis (캐시/세션)
```

### 주요 구성 요소
- **Nginx**: 리버스 프록시, SSL 터미네이션, 정적 파일 서빙
- **Django/Gunicorn**: 웹 애플리케이션 서버
- **PostgreSQL**: 메인 데이터베이스
- **Redis**: 캐시 및 세션 스토리지
- **Let's Encrypt**: 무료 SSL 인증서

---

## 🖥️ 서버 준비

### 최소 권장 사양
- **CPU**: 2 vCPU
- **RAM**: 4GB
- **Storage**: 20GB SSD
- **OS**: Ubuntu 22.04 LTS

### 1. 서버 기본 설정
```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 필수 패키지 설치
sudo apt install -y docker.io docker-compose git nginx certbot python3-certbot-nginx

# Docker 서비스 시작
sudo systemctl start docker
sudo systemctl enable docker

# 사용자를 docker 그룹에 추가
sudo usermod -aG docker $USER
```

### 2. 프로젝트 클론
```bash
git clone <your-repository-url>
cd labeling_project
```

---

## 🔒 SSL 인증서 획득

### Option 1: Let's Encrypt (권장)

#### 1. 도메인 DNS 설정
도메인 제공업체에서 A 레코드를 서버 IP로 설정:
```
your-domain.com    A    YOUR_SERVER_IP
www.your-domain.com A   YOUR_SERVER_IP
```

#### 2. 초기 SSL 인증서 발급
```bash
# Nginx 임시 설정 (HTTP만)
sudo nginx -t && sudo systemctl restart nginx

# Let's Encrypt 인증서 발급
sudo certbot --nginx -d your-domain.com -d www.your-domain.com

# 자동 갱신 설정
sudo crontab -e
# 다음 라인 추가:
# 0 12 * * * /usr/bin/certbot renew --quiet
```

### Option 2: Cloudflare (대안)

#### 1. Cloudflare 설정
1. 도메인을 Cloudflare에 추가
2. SSL/TLS → Overview → "Full (strict)" 선택
3. SSL/TLS → Edge Certificates → "Always Use HTTPS" 활성화

#### 2. DNS 설정
```
your-domain.com    A    YOUR_SERVER_IP (오렌지 클라우드 활성화)
www.your-domain.com CNAME your-domain.com (오렌지 클라우드 활성화)
```

---

## 🐳 Docker 배포

### 1. 환경 변수 설정
```bash
# .env.production 파일 생성 (production.env.example 참고)
cp production.env.example .env.production

# 실제 값으로 수정
nano .env.production
```

**중요한 환경 변수들:**
```bash
DJANGO_SECRET_KEY=your-super-secret-key-here
DOMAIN_NAME=your-domain.com
DB_PASSWORD=your-strong-database-password
GOOGLE_OAUTH_CLIENT_ID=your-google-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-google-client-secret
```

### 2. 도메인 설정 수정
```bash
# nginx/default.conf 파일에서 도메인 변경
sed -i 's/your-domain.com/actual-domain.com/g' nginx/default.conf
```

### 3. Docker Compose 배포
```bash
# 이미지 빌드 및 컨테이너 시작
docker-compose -f docker-compose.production.yml up -d --build

# 로그 확인
docker-compose -f docker-compose.production.yml logs -f

# 데이터베이스 마이그레이션 (필요시)
docker-compose -f docker-compose.production.yml exec web python manage.py migrate
```

### 4. 슈퍼유저 생성
```bash
docker-compose -f docker-compose.production.yml exec web python manage.py createsuperuser
```

---

## 🔑 Google OAuth 설정

### 1. Google Cloud Console 설정
1. [Google Cloud Console](https://console.cloud.google.com) 접속
2. APIs & Services → Credentials 이동
3. OAuth 2.0 Client ID 수정

### 2. 승인된 JavaScript 원본
```
https://your-domain.com
https://www.your-domain.com
```

### 3. 승인된 리디렉트 URI
```
https://your-domain.com/google-user-auth-callback/
https://your-domain.com/google-admin-auth-callback/
https://your-domain.com/google-drive-auth-callback/
https://www.your-domain.com/google-user-auth-callback/
https://www.your-domain.com/google-admin-auth-callback/
https://www.your-domain.com/google-drive-auth-callback/
```

---

## 🛡️ 보안 설정 확인

### 1. SSL 등급 테스트
- [SSL Labs Test](https://www.ssllabs.com/ssltest/) 에서 A+ 등급 확인

### 2. 보안 헤더 확인
- [Security Headers](https://securityheaders.com/) 에서 보안 헤더 검증

### 3. 방화벽 설정
```bash
# UFW 방화벽 설정
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

### 4. 로그 모니터링
```bash
# Nginx 액세스 로그
sudo tail -f /var/log/nginx/access.log

# 애플리케이션 로그
docker-compose -f docker-compose.production.yml logs -f web
```

---

## 📊 모니터링 및 유지보수

### 1. 자동 백업 스크립트
```bash
#!/bin/bash
# backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/var/backups/labeling_project"

mkdir -p $BACKUP_DIR

# 데이터베이스 백업
docker-compose -f docker-compose.production.yml exec -T db pg_dump -U $DB_USER $DB_NAME > $BACKUP_DIR/db_$DATE.sql

# 미디어 파일 백업
tar -czf $BACKUP_DIR/media_$DATE.tar.gz media/

# 오래된 백업 삭제 (30일 이상)
find $BACKUP_DIR -name "*.sql" -o -name "*.tar.gz" -mtime +30 -delete
```

### 2. 시스템 모니터링
```bash
# 컨테이너 상태 확인
docker-compose -f docker-compose.production.yml ps

# 시스템 리소스 확인
docker stats

# 디스크 사용량 확인
df -h
```

### 3. 업데이트 절차
```bash
# 1. 백업 수행
./backup.sh

# 2. 코드 업데이트
git pull origin main

# 3. 컨테이너 재빌드
docker-compose -f docker-compose.production.yml up -d --build

# 4. 마이그레이션 실행
docker-compose -f docker-compose.production.yml exec web python manage.py migrate
```

---

## 🚨 문제 해결

### 일반적인 문제들

#### 1. SSL 인증서 오류
```bash
# 인증서 갱신
sudo certbot renew --dry-run

# Nginx 설정 테스트
sudo nginx -t
```

#### 2. 데이터베이스 연결 오류
```bash
# PostgreSQL 컨테이너 로그 확인
docker-compose -f docker-compose.production.yml logs db

# 데이터베이스 연결 테스트
docker-compose -f docker-compose.production.yml exec web python manage.py dbshell
```

#### 3. Google OAuth 오류
- 리디렉트 URI 확인
- 클라이언트 ID/Secret 환경 변수 확인
- 도메인 인증 상태 확인

#### 4. 성능 문제
```bash
# 리소스 사용량 확인
docker stats

# 로그 크기 제한
docker-compose -f docker-compose.production.yml logs --tail=100 web
```

---

## 📞 지원

문제가 발생하거나 추가 도움이 필요하면:
1. 로그 파일 확인
2. GitHub Issues에 문제 보고
3. 관리자에게 연락

---

**보안은 지속적인 과정입니다. 정기적으로 시스템을 업데이트하고 보안 패치를 적용하세요!** 🔒 