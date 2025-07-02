# Google Drive 이미지 라벨링 서비스 - 리뷰용

## 🎯 프로젝트 목적

### **서비스 개요**
Google Drive에 저장된 이미지들을 웹 인터페이스를 통해 라벨링(분류)할 수 있는 협업 플랫폼

### **주요 기능**
- **Google Drive 연동**: 관리자가 Google Drive의 이미지를 불러와서 배치로 구성
- **협업 라벨링**: 여러 사용자가 동일한 이미지 세트에 대해 라벨링 작업 수행
- **관리자 대시보드**: 전체 진행상황 모니터링 및 사용자 관리
- **배치 관리**: 이미지들을 배치별로 그룹화하여 체계적인 라벨링 작업 진행
- **실시간 통계**: 라벨링 진행률 및 사용자별 성과 추적

### **사용 시나리오**
- **의료 AI 연구**: 임상의사 선생님들이 대량의 학습용 이미지를 라벨링하여 의료 AI 모델 개발에 활용
- **연구 데이터 확장**: 향후 JSON 파일 등 다양한 형태의 데이터를 읽어서 평가받을 수 있도록 확장 예정

### **기술 스택**
- **Backend**: Django (Python)
- **Database**: PostgreSQL
- **Authentication**: Google OAuth 2.0
- **File Storage**: Google Drive API
- **Deployment**: Render (Cloud Platform)
- **Container**: Docker

---

## 🚀 3단계로 바로 실행하기

### 1단계: 환경 설정 (1분)
```bash
# 압축 해제 후 프로젝트 폴더로 이동
cd labeling_project_for_expert

# 환경 변수 파일 생성
cp env.dev.example .env.dev
```

### 2단계: Google OAuth 설정 (2분)
1. https://console.cloud.google.com 접속
2. 새 프로젝트 생성 → Google Drive API 활성화
3. OAuth 2.0 클라이언트 ID 생성 (웹 애플리케이션)
4. 승인된 리디렉션 URI 추가: `http://localhost:8000/google-auth-callback/`
5. `.env.dev` 파일에 클라이언트 ID/시크릿 입력:
```
GOOGLE_OAUTH_CLIENT_ID=your-client-id
GOOGLE_OAUTH_CLIENT_SECRET=your-client-secret
```

### 3단계: 실행 (1분)
```bash
# Docker로 실행
docker-compose -f docker-compose.dev.yml up --build

# 접속: http://localhost:8000
```

---

## 🐛 현재 문제 상황

### 문제 1: 로딩 속도 느림
- **증상**: 로그인/대시보드 페이지 로딩이 5-10초 걸림 
- **원인**: DB 쿼리 최적화 부족, 캐싱 미흡 (Render cold start 문제라고 하는데 괜찮을 때도 있는듯함..?)
- **테스트**: http://localhost:8000/login/ 또는 https://labeling-project-web.onrender.com/login/ 접속 후 로딩 시간 측정

### 문제 2: Google Drive 연동 불안정
- **증상**: OAuth 인증 실패, 이미지 로딩 실패 (관리자 모드에서는 Drive 권한이 있어 이미지가 보이는데, 사용자 모드에서는 보이지 않는 문제)
- **원인**: API 호출 제한, 타임아웃, 프록시 서빙 문제
- **테스트**: 사용자 모드로 Google 로그인 → 이미지 라벨링 페이지 접속 

---

## 🔍 빠른 진단 방법

### 1. 성능 문제 진단
```bash
# 로그 확인
docker-compose -f docker-compose.dev.yml logs web

# 응답 시간 측정
curl -w "시간: %{time_total}초\n" http://localhost:8000/login/
curl -w "시간: %{time_total}초\n" http://localhost:8000/dashboard/
```

### 2. Google Drive 문제 진단
```bash
# OAuth 설정 확인
grep "GOOGLE_OAUTH" .env.dev

# API 호출 로그 확인
docker-compose -f docker-compose.dev.yml logs web | grep "google"
```

### 3. 데이터베이스 문제 진단
```bash
# DB 연결 확인
docker-compose -f docker-compose.dev.yml exec web python manage.py dbshell

# 쿼리 로그 확인 (settings.py에 추가)
LOGGING = {
    'loggers': {
        'django.db.backends': {'level': 'DEBUG'},
    }
}
```

---

## 📁 핵심 파일 위치

| 문제 | 파일 | 설명 |
|------|------|------|
| **성능** | `labeling/views.py` | DB 쿼리 최적화 필요 |
| **성능** | `labeling/models.py` | 인덱스 설정 |
| **Google Drive** | `labeling/views.py` | OAuth/Drive API 로직 |
| **Google Drive** | `labeling/utils.py` | OAuth 설정 |
| **배포** | `render.yaml` | Render 설정 |
| **설정** | `labeling_project/settings_production.py` | 프로덕션 설정 |

---

## 🎯 검토 포인트

### 성능 최적화
1. `labeling/views.py`의 `admin_dashboard()` 함수 - 복잡한 통계 계산
2. `labeling/views.py`의 `dashboard()` 함수 - N+1 쿼리 문제
3. 캐싱 전략 - 현재 5분 캐시만 적용됨

### Google Drive 연동
1. `labeling/views.py`의 `proxy_drive_image()` 함수 - 이미지 프록시 서빙
2. OAuth 토큰 관리 - 리프레시 토큰 처리
3. API 호출 제한 처리 - Rate limiting

### 배포 환경
1. `render.yaml`의 gunicorn 설정 - worker/thread 수
2. 데이터베이스 연결 풀 설정
3. 정적 파일 서빙 최적화

---

## 💡 간단한 테스트 시나리오

### 테스트 1: 기본 로딩 속도
1. http://localhost:8000 또는 https://labeling-project-web.onrender.com/login/ 접속
2. 로그인 페이지 로딩 시간 측정
3. 대시보드 로딩 시간 측정

### 테스트 2: Google Drive 연동
1. 사용자 계정으로 Google 로그인 시도 (관리자 승인 필요)
2. 이미지 라벨링 페이지 접속
3. 이미지 보이는지 확인

### 테스트 3: 관리자 기능
1. 관리자 계정으로 로그인
2. 관리자 대시보드 접속
3. 통계 계산 속도 확인
* 현재 1개 계정으로 하드코딩 되어 있음
---

## 🤔 예상 질문과 답변

### Q1: "로딩 속도가 간헐적으로 느린 이유가 뭔가요?"
**A1: Cold Start + 캐싱 문제**
- Render 무료 플랜 사용 (서버 15분 비활성 시 종료)
- 첫 접속 시 서버 시작 + DB 연결 + 캐싱 초기화로 5-10초
- 이후 접속은 1-2초로 정상
- 해결: Render 유료 플랜 또는 캐시 워밍업 전략

### Q2: "관리자 모드에서는 이미지가 보이는데 사용자 모드에서는 안 보이는 이유가 뭔가요?"
**A2: 권한 및 OAuth 스코프 차이**
- 관리자: Google Drive API 전체 접근 권한
- 사용자: 제한된 OAuth 스코프 (drive.readonly)
- proxy_drive_image() 함수에서 사용자 권한 확인 로직 부족
- 해결: 사용자별 Drive 권한 확인 로직 추가

### Q3: "현재 DB 쿼리 최적화를 했다고 하셨는데, 실제로 개선되었는지 어떻게 확인했나요?"
**A3: 부분적 개선 + 추가 최적화 필요**
- 적용: select_related, prefetch_related, 모델 인덱스 추가
- 문제: admin_dashboard()에서 복잡한 통계 계산 (여러 count 쿼리)
- 현재: 로그인 페이지 15-20개 쿼리 → 목표: 5개 이하
- 해결: 실시간 집계 대신 캐싱된 통계 사용

### Q4: "Google Drive API 호출 제한에 대한 처리가 있나요?"
**A4: 기본적인 처리만 있음**
- 현재: 간단한 에러 핸들링, 접근 로그
- 부족: Rate limiting, 토큰 리프레시, 재시도 메커니즘
- 해결: google-api-python-client의 retry 로직 활용

### Q5: "실서비스 환경에서 이 아키텍처가 적절한가요?"
**A5: 현재는 MVP 수준, 실서비스용 개선 필요**
- 현재: Docker + PostgreSQL + Redis + HTTPS
- 부족: 로드 밸런싱, 백업 전략, 모니터링, CDN
- 권장: AWS/GCP + RDS + ElastiCache + CloudFront + ALB

### Q6: "그럼 왜 물어봤냐?"
**A6: 개발자로서의 한계와 실무 경험 부족**
- 문제를 파악했지만 "이게 최선인가?" 의문
- 실제 운영 환경에서의 경험 부족
- 시간과 리소스의 한계 (몇 주 걸릴 수 있는 최적화)
- 코드 리뷰를 통한 품질 검증 필요
- 실무 노하우와 엣지 케이스 학습 필요

---

## 📞 결론

개선해나갈 점: 

1. **로딩 속도를 3초 이내로 개선하는 방법**
2. **Google Drive 연동 안정성을 높이는 방법**
3. **현재 코드에서 성능 병목 지점**
4. **실서비스 환경에서 추천하는 설정**

**실행 중 문제 발생 시**: `docker-compose -f docker-compose.dev.yml logs web` 로그 확인 후 알려주세용
