from django.core.management.base import BaseCommand
from labeling.models import Batch
from labeling.thumbnail_utils import get_batch_thumbnail_url

class Command(BaseCommand):
    help = '배치별 썸네일 상태를 확인합니다'

    def handle(self, *args, **options):
        self.stdout.write("=== 배치 썸네일 디버깅 정보 ===\n")
        
        # 모든 배치 정보
        all_batches = Batch.objects.all().order_by('id')
        self.stdout.write(f"전체 배치 수: {all_batches.count()}")
        
        # 활성 배치 정보
        active_batches = Batch.objects.filter(is_active=True)
        self.stdout.write(f"활성 배치 수: {active_batches.count()}\n")
        
        self.stdout.write("--- 모든 배치 상세 정보 ---")
        for batch in all_batches:
            images_count = batch.images.count()
            first_image = batch.images.first()
            thumbnail_url = get_batch_thumbnail_url(batch)
            
            self.stdout.write(f"배치 ID: {batch.id}")
            self.stdout.write(f"  이름: {batch.name}")
            self.stdout.write(f"  활성: {batch.is_active}")
            self.stdout.write(f"  이미지 수: {images_count}")
            self.stdout.write(f"  첫 번째 이미지: {first_image}")
            if first_image:
                self.stdout.write(f"    - URL: {first_image.url}")
                self.stdout.write(f"    - Drive ID: {first_image.drive_file_id}")
            self.stdout.write(f"  썸네일 URL: {thumbnail_url}")
            self.stdout.write("---")
        
        self.stdout.write("\n=== 관리자/사용자 모드 차이 분석 ===")
        self.stdout.write("관리자 모드: 모든 배치 표시")
        self.stdout.write("사용자 모드: 활성 배치만 표시")
        
        inactive_batches = Batch.objects.filter(is_active=False)
        if inactive_batches.exists():
            self.stdout.write(f"\n⚠️  비활성 배치 {inactive_batches.count()}개 발견:")
            for batch in inactive_batches:
                self.stdout.write(f"  - {batch.name} (ID: {batch.id})")
                
        self.stdout.write("\n✅ 디버깅 완료!") 