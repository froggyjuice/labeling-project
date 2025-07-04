from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

class Command(BaseCommand):
    help = '등록된 모든 사용자 정보를 출력합니다'

    def add_arguments(self, parser):
        parser.add_argument(
            '--role',
            type=str,
            help='특정 역할의 사용자만 조회 (user/admin)'
        )
        parser.add_argument(
            '--approved',
            action='store_true',
            help='승인된 사용자만 조회'
        )
        parser.add_argument(
            '--pending',
            action='store_true',
            help='승인 대기 중인 사용자만 조회'
        )

    def handle(self, *args, **options):
        User = get_user_model()
        users = User.objects.all()

        # 필터링
        if options['role']:
            users = users.filter(role=options['role'])
        
        if options['approved']:
            users = users.filter(is_approved=True)
        
        if options['pending']:
            users = users.filter(is_approved=False)

        if not users.exists():
            self.stdout.write(
                self.style.WARNING('조건에 맞는 사용자가 없습니다.')
            )
            return

        self.stdout.write(
            self.style.SUCCESS(f'총 {users.count()}명의 사용자를 찾았습니다.\n')
        )

        for user in users:
            status = "승인됨" if user.is_approved else "승인 대기"
            last_login = user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else "로그인 기록 없음"
            
            self.stdout.write(
                f"사용자명: {user.username}\n"
                f"이메일: {user.email}\n"
                f"역할: {user.get_role_display()}\n"
                f"상태: {status}\n"
                f"가입일: {user.date_joined.strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"마지막 로그인: {last_login}\n"
                f"{'='*50}"
            ) 