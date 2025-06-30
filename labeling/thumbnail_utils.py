"""
배치 썸네일 유틸리티 모듈
- 안정적인 썸네일 URL 생성
- Google Drive 프록시 URL 처리
- 업데이트 시 보호되는 핵심 모듈
"""

from django.urls import reverse

def get_batch_thumbnail_url(batch):
    """
    배치의 첫 번째 이미지를 썸네일로 사용하는 안전한 함수
    
    Args:
        batch: Batch 모델 인스턴스
        
    Returns:
        str: 썸네일 URL 또는 기본 이미지 URL
    """
    try:
        # 배치의 첫 번째 이미지 가져오기
        first_image = batch.images.first()
        
        if not first_image:
            return get_default_thumbnail_url()
        
        # Google Drive 이미지인 경우 프록시 URL 생성
        if first_image.drive_file_id:
            return f"/proxy/drive/{first_image.drive_file_id}/"
        
        # 일반 이미지인 경우 직접 URL 사용
        return first_image.url
        
    except Exception as e:
        print(f"[WARNING] 썸네일 생성 실패 (배치 ID: {batch.id}): {str(e)}")
        return get_default_thumbnail_url()

def get_default_thumbnail_url():
    """
    기본 썸네일 URL 반환 (Fallback 포함)
    
    Returns:
        str: 기본 썸네일 이미지 URL 또는 Data URL
    """
    # 1차: 기본 이미지 파일 사용
    default_image_path = "/static/images/default-batch-thumbnail.png"
    
    # 2차: 파일이 없는 경우 SVG Data URL 사용 (즉시 표시)
    fallback_svg = "data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMjAwIiBoZWlnaHQ9IjE1MCIgdmlld0JveD0iMCAwIDIwMCAxNTAiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxyZWN0IHdpZHRoPSIyMDAiIGhlaWdodD0iMTUwIiBmaWxsPSIjRjhGOUZBIiBzdHJva2U9IiNEOURFRTIiIHN0cm9rZS13aWR0aD0iMiIgc3Ryb2tlLWRhc2hhcnJheT0iNSA1Ii8+Cjx0ZXh0IHg9IjEwMCIgeT0iNzAiIGZvbnQtZmFtaWx5PSJBcmlhbCwgc2Fucy1zZXJpZiIgZm9udC1zaXplPSIxNCIgZmlsbD0iIzZDNzU3RCIgdGV4dC1hbmNob3I9Im1pZGRsZSI+7J207Jq47KeAIOyXhuydjDwvdGV4dD4KPHRleHQgeD0iMTAwIiB5PSI5MCIgZm9udC1mYW1pbHk9IkFyaWFsLCBzYW5zLXNlcmlmIiBmb250LXNpemU9IjEyIiBmaWxsPSIjNkM3NTdEIiB0ZXh0LWFuY2hvcj0ibWlkZGxlIj7qs4Xqs6Ig7J6R7JeF7ZWY7IS464qUIPC9saFCBDHRleCg+PC9zdmc+"
    
    return default_image_path

def get_image_proxy_url(image):
    """
    개별 이미지의 프록시 URL 생성
    
    Args:
        image: Image 모델 인스턴스
        
    Returns:
        str: 프록시 URL 또는 직접 URL
    """
    try:
        if image.drive_file_id:
            return f"/proxy/drive/{image.drive_file_id}/"
        return image.url
    except Exception as e:
        print(f"[WARNING] 이미지 프록시 URL 생성 실패: {str(e)}")
        return "/static/images/image-error.png"

def validate_batch_thumbnails(batches):
    """
    여러 배치의 썸네일 URL을 일괄 검증 및 생성
    
    Args:
        batches: Batch 쿼리셋 또는 리스트
        
    Returns:
        list: 썸네일 URL이 추가된 배치 데이터 리스트
    """
    batch_data = []
    
    for batch in batches:
        try:
            thumbnail_url = get_batch_thumbnail_url(batch)
            
            batch_info = {
                'id': batch.id,
                'name': batch.name,
                'thumbnail_url': thumbnail_url,
                'image_count': batch.images.count(),
                'has_images': batch.images.exists(),
                'first_image_type': 'drive' if batch.images.first() and batch.images.first().drive_file_id else 'url'
            }
            
            batch_data.append(batch_info)
            
        except Exception as e:
            print(f"[ERROR] 배치 검증 실패 (ID: {batch.id}): {str(e)}")
            # 오류 발생 시 기본 데이터 추가
            batch_data.append({
                'id': batch.id,
                'name': batch.name,
                'thumbnail_url': get_default_thumbnail_url(),
                'image_count': 0,
                'has_images': False,
                'first_image_type': 'error'
            })
    
    return batch_data

# 모듈 안정성 체크
def check_thumbnail_system_health():
    """
    썸네일 시스템의 건강성 체크
    
    Returns:
        dict: 시스템 상태 정보
    """
    from .models import Batch
    
    try:
        total_batches = Batch.objects.count()
        batches_with_images = Batch.objects.filter(images__isnull=False).distinct().count()
        drive_images_count = Batch.objects.filter(images__drive_file_id__isnull=False).distinct().count()
        
        return {
            'status': 'healthy',
            'total_batches': total_batches,
            'batches_with_images': batches_with_images,
            'drive_images_count': drive_images_count,
            'health_percentage': (batches_with_images / total_batches * 100) if total_batches > 0 else 0
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'health_percentage': 0
        } 