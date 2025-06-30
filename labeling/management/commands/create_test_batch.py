from django.core.management.base import BaseCommand
from labeling.models import Batch, Image

class Command(BaseCommand):
    help = '테스트용 배치와 이미지를 생성합니다'

    def handle(self, *args, **options):
        self.stdout.write("=== 테스트용 배치 생성 ===\n")
        
        # 활성 배치 생성
        active_batch = Batch.objects.create(
            name="테스트 활성 배치",
            is_active=True
        )
        
        # 비활성 배치 생성
        inactive_batch = Batch.objects.create(
            name="테스트 비활성 배치", 
            is_active=False
        )
        
        # 활성 배치에 이미지 추가
        Image.objects.create(
            batch=active_batch,
            url="https://via.placeholder.com/300x200/0066cc/ffffff?text=Active+Image+1",
            drive_file_id=None
        )
        
        Image.objects.create(
            batch=active_batch,
            url="https://via.placeholder.com/300x200/00cc66/ffffff?text=Active+Image+2",
            drive_file_id=None
        )
        
        # 비활성 배치에 이미지 추가
        Image.objects.create(
            batch=inactive_batch,
            url="https://via.placeholder.com/300x200/cc6600/ffffff?text=Inactive+Image+1",
            drive_file_id=None
        )
        
        self.stdout.write(f"✅ 활성 배치 생성: {active_batch.name} (ID: {active_batch.id})")
        self.stdout.write(f"✅ 비활성 배치 생성: {inactive_batch.name} (ID: {inactive_batch.id})")
        self.stdout.write(f"📁 활성 배치 이미지: {active_batch.images.count()}개")
        self.stdout.write(f"📁 비활성 배치 이미지: {inactive_batch.images.count()}개")
        
        self.stdout.write("\n=== 테스트 배치 생성 완료! ===")
        self.stdout.write("이제 관리자/사용자 대시보드에서 차이를 확인할 수 있습니다:")
        self.stdout.write("- 관리자 모드: 활성 + 비활성 배치 모두 표시")
        self.stdout.write("- 사용자 모드: 활성 배치만 표시") 