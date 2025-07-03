# Django 관리자 인터페이스 설정
from django.contrib import admin
from .models import User, Batch, Image, LabelingResult

# 사용자 모델을 관리자 인터페이스에 등록
# - 사용자 계정 관리, 승인, 역할 변경 등 가능
admin.site.register(User)

# 배치 모델을 관리자 인터페이스에 등록
# - 이미지 배치 생성, 수정, 활성화/비활성화 관리
admin.site.register(Batch)

# 이미지 모델을 관리자 인터페이스에 등록
# - 이미지 파일 정보 관리, Google Drive 연동 상태 확인
admin.site.register(Image)

# 라벨링 결과 모델을 관리자 인터페이스에 등록
# - 사용자별 라벨링 결과 조회, 통계 확인
admin.site.register(LabelingResult) 