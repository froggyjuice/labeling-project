# 마이그레이션 히스토리

이 폴더는 데이터베이스 스키마 변경 이력을 관리합니다. 각 마이그레이션 파일은 특정 시점의 데이터베이스 구조 변경사항을 정의합니다.

## 마이그레이션 순서 및 설명

### 0001_initial.py
**초기 데이터베이스 스키마 생성**
- 기본 모델들 생성: User, Batch, Label, Image, LabelingResult
- 이미지 라벨링 시스템의 핵심 구조 구축

### 0002_user_approved_at_user_approved_by_user_google_id_and_more.py
**사용자 승인 시스템 및 역할 관리**
- `approved_at`: 사용자 승인 시간
- `approved_by`: 승인한 관리자 (외래키)
- `role`: 사용자 역할 (user/admin)
- `google_id`: Google 계정 연동 ID

### 0003_batch_created_at_batch_is_active.py
**배치 관리 기능 강화**
- `created_at`: 배치 생성 시간
- `is_active`: 배치 활성/비활성 상태

### 0004_alter_labelingresult_unique_together_imageaccesslog.py
**데이터 무결성 및 보안 모니터링**
- 라벨링 결과 고유 제약조건 추가 (한 사용자당 한 이미지에 하나의 결과만)
- ImageAccessLog 모델 생성 (이미지 접근 추적)

### 0005_message.py
**사용자-관리자 소통 시스템**
- Message 모델 생성
- 메시지 전송, 답변, 읽음 상태 관리
- 전역 메시지 및 배치별 메시지 지원

### 0006_user_google_name_user_google_picture.py
**Google OAuth 프로필 연동 (사용 중단)**
- `google_name`: Google 계정 표시명
- `google_picture`: Google 프로필 사진 URL
- **참고**: IAM 방식으로 전환 후 사용되지 않음

### 0007_batch_labeling_ba_is_acti_627d62_idx_and_more.py
**데이터베이스 성능 최적화**
- 배치, 이미지, 라벨링 결과 조회 속도 향상
- 복합 인덱스 및 단일 인덱스 추가

### 0008_remove_google_oauth_fields.py
**IAM 서비스 계정 방식으로 전환**
- `google_id`, `google_name`, `google_picture` 필드 제거
- Google OAuth 의존성 완전 제거
- IAM 서비스 계정 기반 인증 시스템으로 완전 전환

## 마이그레이션 실행 방법

```bash
# 마이그레이션 적용
python manage.py migrate

# 마이그레이션 상태 확인
python manage.py showmigrations

# 특정 마이그레이션으로 되돌리기
python manage.py migrate labeling 0003
```

## 주의사항

- 마이그레이션 파일명은 변경하지 마세요 (의존성 문제 발생 가능)
- 프로덕션 환경에서는 마이그레이션을 신중하게 적용하세요
- 데이터베이스 백업을 먼저 수행하세요
- 0006 마이그레이션은 IAM 방식 전환으로 인해 더 이상 사용되지 않습니다 