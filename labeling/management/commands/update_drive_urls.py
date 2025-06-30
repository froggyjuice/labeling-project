from django.core.management.base import BaseCommand
from labeling.models import Image

class Command(BaseCommand):
    help = 'Update Google Drive image URLs to use proxy URLs'

    def handle(self, *args, **options):
        # drive_file_id가 있는 이미지들을 찾아서 URL 업데이트
        images = Image.objects.filter(drive_file_id__isnull=False)
        
        updated_count = 0
        for image in images:
            if image.drive_file_id:
                # 프록시 URL로 업데이트
                new_url = f"/proxy-drive-image/{image.drive_file_id}/"
                if image.url != new_url:
                    image.url = new_url
                    image.save()
                    updated_count += 1
                    self.stdout.write(f"Updated: {image.file_name}")
        
        self.stdout.write(
            self.style.SUCCESS(f'Successfully updated {updated_count} image URLs')
        ) 