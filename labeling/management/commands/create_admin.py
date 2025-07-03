from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = '관리자 계정을 생성합니다'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, default='admin', help='관리자 사용자명')
        parser.add_argument('--email', type=str, default='admin@example.com', help='관리자 이메일')
        parser.add_argument('--password', type=str, default='admin1234', help='관리자 비밀번호')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        
        try:
            # 기존 사용자 확인
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'사용자 "{username}"이(가) 이미 존재합니다.')
                )
                return
            
            # 관리자 계정 생성
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                role='admin',
                is_approved=True,
                is_staff=True,
                is_superuser=True,
                approved_at=timezone.now()
            )
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'관리자 계정이 성공적으로 생성되었습니다!\n'
                    f'사용자명: {username}\n'
                    f'이메일: {email}\n'
                    f'비밀번호: {password}'
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'관리자 계정 생성 중 오류가 발생했습니다: {str(e)}')
            ) 