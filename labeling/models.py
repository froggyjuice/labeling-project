from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    USER_ROLES = (
        ('user', '사용자'),
        ('admin', '관리자'),
    )
    
    role = models.CharField(max_length=10, choices=USER_ROLES, default='user')
    is_approved = models.BooleanField(default=False)  # 관리자 승인 여부
    google_id = models.CharField(max_length=255, unique=True, null=True, blank=True)
    google_name = models.CharField(max_length=255, null=True, blank=True)  # Google에서 가져온 이름
    google_picture = models.URLField(null=True, blank=True)  # Google 프로필 사진 URL
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)

class Batch(models.Model):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)  # 배치 활성화 상태
    created_at = models.DateTimeField(null=True, blank=True)  # 생성 시간
    
    def __str__(self):
        return self.name

class Image(models.Model):
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='images')
    file_name = models.CharField(max_length=255)
    url = models.URLField()
    drive_file_id = models.CharField(max_length=255, blank=True, null=True)
    def __str__(self):
        return self.file_name

class Label(models.Model):
    name = models.CharField(max_length=50)  # 긍정적, 부정적, 중립적 등

class LabelingResult(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    labels = models.ManyToManyField(Label)  # 다중 선택 지원
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user', 'image']  # 한 사용자는 한 이미지에 하나의 라벨만
    
    def __str__(self):
        return f"{self.user.email} - {self.image.file_name}: {self.labels.all()}"

class ImageAccessLog(models.Model):
    """이미지 접근 로그 - 보안 모니터링"""
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_file_id = models.CharField(max_length=200)  # Google Drive file ID
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField(blank=True)
    access_time = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-access_time']
        indexes = [
            models.Index(fields=['user', 'access_time']),
            models.Index(fields=['image_file_id', 'access_time']),
            models.Index(fields=['ip_address', 'access_time']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.image_file_id} at {self.access_time}"

class Message(models.Model):
    """사용자가 관리자에게 보내는 메시지"""
    MESSAGE_TYPES = (
        ('global', '전역 메시지'),
        ('batch', '배치별 메시지'),
    )
    
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPES)
    subject = models.CharField(max_length=200)  # 메시지 제목
    content = models.TextField()  # 메시지 내용
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, null=True, blank=True)  # 배치별 메시지인 경우
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)  # 관리자가 읽었는지 여부
    admin_reply = models.TextField(blank=True, null=True)  # 관리자 답변
    replied_at = models.DateTimeField(null=True, blank=True)  # 답변 시간
    replied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='replied_messages')
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['sender', 'created_at']),
            models.Index(fields=['message_type', 'created_at']),
            models.Index(fields=['is_read', 'created_at']),
        ]
    
    def __str__(self):
        batch_info = f" ({self.batch.name})" if self.batch else ""
        return f"{self.sender.email}: {self.subject}{batch_info}" 