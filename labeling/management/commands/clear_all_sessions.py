from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session

class Command(BaseCommand):
    help = 'Clear all Django sessions'

    def handle(self, *args, **options):
        # 모든 세션 삭제
        session_count = Session.objects.count()
        Session.objects.all().delete()
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully cleared {session_count} sessions')
        )
        
        self.stdout.write(
            self.style.WARNING('모든 사용자가 다시 로그인해야 합니다.')
        ) 