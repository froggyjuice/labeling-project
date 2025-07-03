# Django 모델 정의 - 이미지 라벨링 시스템의 데이터 구조
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """사용자 모델 - Django 기본 User 모델을 확장"""
    USER_ROLES = (
        ('user', '사용자'),
        ('admin', '관리자'),
    )
    
    role = models.CharField(max_length=10, choices=USER_ROLES, default='user')  # 사용자 역할 (사용자/관리자)
    is_approved = models.BooleanField(default=False)  # 관리자 승인 여부
    approved_at = models.DateTimeField(null=True, blank=True)  # 승인된 시간
    approved_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)  # 승인한 관리자

class Batch(models.Model):
    """이미지 배치 모델 - 이미지들을 그룹화하는 단위"""
    name = models.CharField(max_length=100)  # 배치 이름
    is_active = models.BooleanField(default=True)  # 배치 활성화 상태
    created_at = models.DateTimeField(null=True, blank=True)  # 생성 시간
    
    class Meta:
        indexes = [
            models.Index(fields=['is_active', 'created_at']),  # 활성 배치를 생성 시간순으로 빠르게 조회
            models.Index(fields=['name']),  # 배치 이름으로 빠른 검색
        ]
    
    def __str__(self):
        return self.name

class Image(models.Model):
    """이미지 모델 - 라벨링할 이미지 정보"""
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='images')  # 배치와의 관계 (배치 삭제 시 이미지도 삭제)
    file_name = models.CharField(max_length=255)  # 파일명
    url = models.URLField()  # 이미지 URL
    drive_file_id = models.CharField(max_length=255, blank=True, null=True)  # Google Drive 파일 ID
    
    class Meta:
        indexes = [
            models.Index(fields=['batch', 'file_name']),  # 특정 배치의 이미지를 파일명순으로 빠르게 조회
            models.Index(fields=['drive_file_id']),  # Google Drive 파일 ID로 빠른 검색
        ]
    
    def __str__(self):
        return self.file_name

class Label(models.Model):
    """라벨 모델 - 이미지에 붙일 수 있는 태그들"""
    name = models.CharField(max_length=50)  # 긍정적, 부정적, 중립적 등
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),  # 라벨 이름으로 빠른 검색
        ]

class LabelingResult(models.Model):
    """라벨링 결과 모델 - 사용자가 이미지에 붙인 라벨 정보"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 라벨링한 사용자 (사용자 삭제 시 결과도 삭제)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)  # 라벨링된 이미지 (이미지 삭제 시 결과도 삭제)
    labels = models.ManyToManyField(Label)  # 다중 선택 지원 (여러 라벨 선택 가능)
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시간 (자동 기록)
    updated_at = models.DateTimeField(auto_now=True)  # 수정 시간 (자동 업데이트)

    class Meta:
        unique_together = ['user', 'image']  # 한 사용자는 한 이미지에 하나의 라벨링 결과만 가질 수 있음
        indexes = [
            models.Index(fields=['user', 'image']),  # 특정 사용자의 특정 이미지 결과를 빠르게 조회
            models.Index(fields=['created_at']),  # 생성 시간순으로 결과를 빠르게 조회
            models.Index(fields=['updated_at']),  # 수정 시간순으로 결과를 빠르게 조회
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.image.file_name}: {self.labels.all()}"

class ImageAccessLog(models.Model):
    """이미지 접근 로그 - 보안 모니터링 및 접근 추적"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # 접근한 사용자 (사용자 삭제 시 로그도 삭제)
    image_file_id = models.CharField(max_length=200)  # Google Drive file ID
    ip_address = models.GenericIPAddressField()  # 접근한 IP 주소
    user_agent = models.TextField(blank=True)  # 사용자 브라우저 정보
    access_time = models.DateTimeField(auto_now_add=True)  # 접근 시간 (자동 기록)
    success = models.BooleanField(default=True)  # 접근 성공 여부
    error_message = models.TextField(blank=True)  # 오류 메시지 (접근 실패 시)
    
    class Meta:
        ordering = ['-access_time']  # 접근 시간 역순으로 정렬 (최신순)
        indexes = [
            models.Index(fields=['user', 'access_time']),  # 사용자별 접근 시간 인덱스
            models.Index(fields=['image_file_id', 'access_time']),  # 이미지별 접근 시간 인덱스
            models.Index(fields=['ip_address', 'access_time']),  # IP별 접근 시간 인덱스
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.image_file_id} at {self.access_time}"

class Message(models.Model):
    """사용자가 관리자에게 보내는 메시지 - 소통 시스템"""
    MESSAGE_TYPES = (
        ('global', '전역 메시지'),
        ('batch', '배치별 메시지'),
    )
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')  # 메시지 발신자 (사용자 삭제 시 메시지도 삭제)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)  # 메시지 유형 (전역/배치별)
    subject = models.CharField(max_length=200)  # 메시지 제목
    content = models.TextField()  # 메시지 내용
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)  # 관련 배치 (배치별 메시지인 경우, 배치 삭제 시 메시지도 삭제)
    created_at = models.DateTimeField(auto_now_add=True)  # 생성 시간 (자동 기록)
    is_read = models.BooleanField(default=False)  # 관리자가 읽었는지 여부
    admin_reply = models.TextField(blank=True, null=True)  # 관리자 답변 내용
    replied_at = models.DateTimeField(null=True, blank=True)  # 답변 시간
    replied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='replied_messages')  # 답변한 관리자 (관리자 삭제 시 답변자 정보는 NULL로 설정)
    
    class Meta:
        ordering = ['-created_at']  # 생성 시간 역순으로 정렬 (최신순)
        indexes = [
            models.Index(fields=['sender', 'created_at']),  # 발신자별 생성 시간 인덱스
            models.Index(fields=['message_type', 'created_at']),  # 메시지 유형별 생성 시간 인덱스
            models.Index(fields=['is_read', 'created_at']),  # 읽음 상태별 생성 시간 인덱스
        ]
    
    def __str__(self):
        batch_info = f" ({self.batch.name})" if self.batch else ""
        return f"{self.sender.email}: {self.subject}{batch_info}" 