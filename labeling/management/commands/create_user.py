from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Command(BaseCommand):
    help = '사용자 계정을 생성합니다 (승인 대기 상태)'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True, help='사용자명')
        parser.add_argument('--email', type=str, required=True, help='사용자 이메일')
        parser.add_argument('--password', type=str, default='user1234', help='사용자 비밀번호')
        parser.add_argument('--first-name', type=str, help='이름')
        parser.add_argument('--last-name', type=str, help='성')
        parser.add_argument('--auto-approve', action='store_true', help='자동 승인 (기본값: 승인 대기)')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        first_name = options.get('first_name', '')
        last_name = options.get('last_name', '')
        auto_approve = options['auto_approve']
        
        try:
            # 기존 사용자 확인
            if User.objects.filter(username=username).exists():
                self.stdout.write(
                    self.style.WARNING(f'사용자명 "{username}"이(가) 이미 존재합니다.')
                )
                return
            
            if User.objects.filter(email=email).exists():
                self.stdout.write(
                    self.style.WARNING(f'이메일 "{email}"이(가) 이미 사용 중입니다.')
                )
                return
            
            # 사용자 계정 생성
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                role='user',
                is_approved=auto_approve,
                is_staff=False,
                is_superuser=False
            )
            
            # 자동 승인인 경우 승인 정보 설정
            if auto_approve:
                user.approved_at = timezone.now()
                # 관리자 계정을 승인자로 설정 (첫 번째 관리자 계정)
                admin_user = User.objects.filter(role='admin', is_approved=True).first()
                if admin_user:
                    user.approved_by = admin_user
                user.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f'사용자 계정이 성공적으로 생성되고 승인되었습니다!\n'
                        f'사용자명: {username}\n'
                        f'이메일: {email}\n'
                        f'비밀번호: {password}\n'
                        f'이름: {first_name} {last_name}\n'
                        f'상태: 승인됨 ✅'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'사용자 계정이 성공적으로 생성되었습니다! (승인 대기)\n'
                        f'사용자명: {username}\n'
                        f'이메일: {email}\n'
                        f'비밀번호: {password}\n'
                        f'이름: {first_name} {last_name}\n'
                        f'상태: 승인 대기 ⏳\n'
                        f'관리자 대시보드에서 승인해주세요.'
                    )
                )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'사용자 계정 생성 중 오류가 발생했습니다: {str(e)}')
            ) 