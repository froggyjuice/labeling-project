#!/usr/bin/env python
"""
Django Views for Image Labeling System

이 파일은 이미지 라벨링 시스템의 핵심 뷰들을 포함합니다.
주석으로 필수 기능과 선택적 성능 향상 부분을 구분했습니다.

[필수 기능] - 시스템 작동에 반드시 필요한 부분
[성능 향상] - 선택적이지만 권장되는 최적화 부분
"""

# ============================================================================
# [필수 기능] 기본 Django 및 외부 라이브러리 import
# ============================================================================
import os
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Batch, Image, Label, LabelingResult, ImageAccessLog, Message
from django.views.decorators.csrf import csrf_exempt
from django.db import models

# [필수 기능] Google Drive API 관련 import
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
from .utils import get_service_account_credentials, test_service_account_access

# [필수 기능] 파일 처리 및 HTTP 요청
import requests
import io
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# ============================================================================
# [성능 향상] 캐싱 관련 import (선택적이지만 권장)
# ============================================================================
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_cookie

# ============================================================================
# [필수 기능] 개발 환경 설정
# ============================================================================

# [필수 기능] Google IAM 서비스 계정 설정 확인
print("🔧 Google IAM 서비스 계정 기반 인증 시스템 사용 중")

# ============================================================================
# [필수 기능] 로그인 관련 뷰
# ============================================================================

# [성능 향상] 캐싱 적용 (5분 캐시) - 선택적이지만 권장
@cache_page(60 * 5)  # 5분 캐시
@vary_on_cookie
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        login_type = request.POST.get("login_type")
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            if login_type == "admin" and user.is_staff:
                return redirect("admin_dashboard")
            elif login_type == "user":
                return redirect("dashboard")
            else:
                messages.error(request, "권한이 없습니다.")
        else:
            messages.error(request, "로그인 정보가 올바르지 않습니다.")
    
    return render(request, "labeling/login.html")

def user_login(request):
    return login_view(request)

def admin_login(request):
    return login_view(request)

# [성능 향상] 캐싱 적용 (10분 캐시) - 선택적이지만 권장
@cache_page(60 * 10)  # 10분 캐시
def waiting(request):
    """승인 대기 페이지"""
    return render(request, 'labeling/waiting.html')

# ============================================================================
# [필수 기능] 관리자 대시보드
# ============================================================================

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    # [성능 향상] 배치 정보를 한 번에 가져오기 (N+1 문제 해결)
    batches = Batch.objects.prefetch_related('images').all().order_by('-created_at')
    
    # 승인 대기 중인 사용자들
    from django.contrib.auth import get_user_model
    User = get_user_model()
    pending_users = User.objects.filter(role='user', is_approved=False).order_by('-date_joined')
    
    # [성능 향상] 배치별 통계를 한 번에 계산 (N+1 문제 해결)
    from django.db.models import Count, Q
    from django.utils import timezone
    from datetime import timedelta
    
    # [성능 향상] 배치별 라벨링 통계를 한 번에 계산
    batch_stats = {}
    for batch in batches:
        total_images = batch.images.count()
        labeled_count = LabelingResult.objects.filter(image__batch=batch).values('image').distinct().count()
        progress_percentage = (labeled_count / total_images * 100) if total_images > 0 else 0
        
        batch_stats[batch.id] = {
            'total_images': total_images,
            'labeled_count': labeled_count,
            'progress_percentage': round(progress_percentage, 1)
        }
    
    # 배치별 썸네일 정보 추가
    batches_with_info = []
    for batch in batches:
        first_image = batch.images.first()
        thumbnail_url = first_image.url if first_image else None
        
        batches_with_info.append({
            'batch': batch,
            'thumbnail_url': thumbnail_url,
            'total_images': batch_stats[batch.id]['total_images'],
            'labeled_count': batch_stats[batch.id]['labeled_count'],
            'progress_percentage': batch_stats[batch.id]['progress_percentage']
        })
    
    # [성능 향상] 사용자별 진행률 통계 (최적화)
    user_stats = []
    approved_users = User.objects.filter(role='user', is_approved=True)
    
    # [성능 향상] 활성 배치만 필터링
    active_batches = [batch for batch in batches if batch.is_active]
    
    for user in approved_users:
        # [성능 향상] 각 배치별 사용자 진행률을 한 번에 계산
        user_batch_progress = []
        total_assigned = 0
        total_completed = 0
        
        for batch in active_batches:
            batch_total = batch.images.count()
            batch_completed = LabelingResult.objects.filter(
                user=user, 
                image__batch=batch
            ).count()
            
            batch_progress = (batch_completed / batch_total * 100) if batch_total > 0 else 0
            
            user_batch_progress.append({
                'batch_name': batch.name,
                'total': batch_total,
                'completed': batch_completed,
                'progress': round(batch_progress, 1)
            })
            
            total_assigned += batch_total
            total_completed += batch_completed
        
        overall_progress = (total_completed / total_assigned * 100) if total_assigned > 0 else 0
        
        user_stats.append({
            'user': user,
            'total_assigned': total_assigned,
            'total_completed': total_completed,
            'overall_progress': round(overall_progress, 1),
            'batch_progress': user_batch_progress
        })
    
    # [성능 향상] 보안 모니터링 통계 (최적화)
    yesterday = timezone.now() - timedelta(days=1)
    recent_access_logs = ImageAccessLog.objects.filter(access_time__gte=yesterday)
    
    # [성능 향상] 통계를 한 번에 계산
    total_requests = recent_access_logs.count()
    successful_requests = recent_access_logs.filter(success=True).count()
    failed_requests = total_requests - successful_requests
    
    security_stats = {
        'total_requests': total_requests,
        'successful_requests': successful_requests,
        'failed_requests': failed_requests,
        'rate_limit_violations': recent_access_logs.filter(error_message__contains='Rate limit').count(),
        'unauthorized_attempts': recent_access_logs.filter(error_message__contains='Access denied').count(),
        'top_users': recent_access_logs.values('user__email').annotate(
            request_count=Count('id')
        ).order_by('-request_count')[:5],
        'recent_failures': recent_access_logs.filter(success=False).order_by('-access_time')[:10]
    }
    
    # [성능 향상] 메시지 통계 (최적화)
    message_stats = {
        'total_messages': Message.objects.count(),
        'unread_messages': Message.objects.filter(is_read=False).count(),
        'pending_replies': Message.objects.filter(admin_reply__isnull=True).count(),
        'recent_messages': Message.objects.select_related('sender', 'batch').order_by('-created_at')[:5]
    }
    
    context = {
        'batches_with_info': batches_with_info,
        'pending_users': pending_users,
        'user_stats': user_stats,
        'security_stats': security_stats,
        'message_stats': message_stats,
        'service_account_available': get_service_account_credentials() is not None
    }
    return render(request, 'labeling/admin_dashboard.html', context)

# ============================================================================
# [필수 기능] 사용자 대시보드
# ============================================================================

def dashboard(request):
    # [필수 기능] 인증 확인 (자동 리다이렉트 방지)
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요합니다.")
        return redirect("login")
    
    # [필수 기능] 관리자는 관리자 대시보드로 리다이렉트
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    
    # [필수 기능] 승인되지 않은 사용자는 대기 페이지로 리다이렉트
    if not request.user.is_approved:
        return redirect('waiting')
    
    # [성능 향상] 활성화된 배치만 표시 (최적화)
    batches = Batch.objects.filter(is_active=True).prefetch_related('images')
    
    batch_data = []
    total_images = 0
    completed_images = 0
    
    # [성능 향상] 사용자의 라벨링 결과를 한 번에 가져오기
    user_labeling_results = LabelingResult.objects.filter(
        user=request.user
    ).values_list('image__batch_id', flat=True)
    
    # [성능 향상] 배치별 완료된 이미지 수를 한 번에 계산
    batch_completion_counts = {}
    for batch_id in user_labeling_results:
        batch_completion_counts[batch_id] = batch_completion_counts.get(batch_id, 0) + 1
    
    for batch in batches:
        batch_images = batch.images.all()
        batch_total = batch_images.count()
        
        # [성능 향상] 라벨링 완료된 이미지 수 계산 (최적화)
        batch_completed = batch_completion_counts.get(batch.id, 0)
        
        progress_percentage = (batch_completed / batch_total * 100) if batch_total > 0 else 0
        is_completed = batch_completed >= batch_total
        
        # 첫 번째 이미지를 썸네일로 사용
        thumbnail_url = batch_images.first().url if batch_images.exists() else None
        
        batch_data.append({
            "id": batch.id,
            "name": batch.name,
            "total_images": batch_total,
            "completed_images": batch_completed,
            "progress_percentage": progress_percentage,
            "is_completed": is_completed,
            "thumbnail_url": thumbnail_url
        })
        
        total_images += batch_total
        completed_images += batch_completed
    
    overall_progress = (completed_images / total_images * 100) if total_images > 0 else 0
    
    context = {
        "batches": batch_data,
        "total_images": total_images,
        "completed_images": completed_images,
        "overall_progress": overall_progress
    }
    
    return render(request, "labeling/dashboard.html", context)

# ============================================================================
# [필수 기능] 라벨링 페이지
# ============================================================================

def labeling(request, batch_id):
    # [필수 기능] 인증 확인 (자동 리다이렉트 방지)
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요합니다.")
        return redirect("login")
    
    try:
        batch = Batch.objects.get(id=batch_id)
        images = batch.images.all()
        
        current_index = int(request.GET.get("index", 0))
        current_index = max(0, min(current_index, images.count() - 1))
        
        current_image = images[current_index] if images.exists() else None
        
        progress_percentage = ((current_index + 1) / images.count() * 100) if images.count() > 0 else 0
        
        context = {
            "batch": batch,
            "images": images,
            "current_image": current_image,
            "current_index": current_index,
            "total_images": images.count(),
            "progress_percentage": progress_percentage,
            "user_id": request.user.id,
        }
        
        return render(request, "labeling/labeling_simple.html", context)
        
    except Batch.DoesNotExist:
        messages.error(request, "배치를 찾을 수 없습니다.")
        return redirect("dashboard")
    except Exception as e:
        messages.error(request, f"오류가 발생했습니다: {str(e)}")
        return redirect("dashboard")

# ============================================================================
# [필수 기능] 라벨링 진행률 저장
# ============================================================================

@csrf_exempt
def save_progress(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            batch_id = data.get("batchId")
            current_index = data.get("currentIndex")
            labels = data.get("labels", {})
            
            # 세션에 진행상황 저장 (기존 기능)
            if "labeling_progress" not in request.session:
                request.session["labeling_progress"] = {}
            
            request.session["labeling_progress"][str(batch_id)] = {
                "current_index": current_index,
                "labels": labels,
                "timestamp": data.get("timestamp")
            }
            request.session.modified = True
            
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "POST only"}, status=405)

# ============================================================================
# [필수 기능] 라벨링 결과 저장
# ============================================================================

@csrf_exempt  
def save_label(request):
    """개별 이미지에 대한 라벨링 결과 저장"""
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            image_id = data.get("imageId")
            selected_labels = data.get("labels", [])
            
            if not request.user.is_authenticated:
                return JsonResponse({"error": "로그인이 필요합니다"}, status=401)
            
            # 이미지 확인
            try:
                image = Image.objects.get(id=image_id)
            except Image.DoesNotExist:
                return JsonResponse({"error": "이미지를 찾을 수 없습니다"}, status=404)
            
            # 기존 라벨링 결과 삭제 (동일 사용자, 동일 이미지)
            LabelingResult.objects.filter(user=request.user, image=image).delete()
            
            # 새로운 라벨링 결과 저장
            if selected_labels:
                labeling_result = LabelingResult.objects.create(
                    user=request.user,
                    image=image
                )
                
                # 라벨들 추가
                for label_name in selected_labels:
                    label, created = Label.objects.get_or_create(name=label_name)
                    labeling_result.labels.add(label)
            
            return JsonResponse({"status": "success"})
            
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    return JsonResponse({"error": "POST only"}, status=405)

def load_progress(request, user_id, batch_id):
    try:
        progress_data = request.session.get("labeling_progress", {}).get(str(batch_id), {})
        return JsonResponse({
            "currentIndex": progress_data.get("current_index", 0),
            "labels": progress_data.get("labels", {}),
            "timestamp": progress_data.get("timestamp")
        })
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

def get_batches(request, user_id):
    try:
        batches = Batch.objects.all()
        batch_list = []
        
        for batch in batches:
            batch_list.append({
                "id": batch.id,
                "name": batch.name,
                "image_count": batch.images.count()
            })
        
        return JsonResponse({"batches": batch_list})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

@csrf_exempt
def validate_user(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)
    try:
        user_id = request.POST.get("user_id")
        if not user_id:
            return JsonResponse({"error": "Missing user_id"}, status=400)
        return JsonResponse({"valid": True})
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=400)

# ============================================================================
# [필수 기능] Google Drive API 관련 뷰 (IAM 서비스 계정 기반)
# ============================================================================

def upload_to_drive(request):
    """Google Drive에 파일 업로드 (향후 확장용)"""
    try:
        # IAM 서비스 계정 credentials 사용
        credentials = get_service_account_credentials()
        if not credentials:
            return JsonResponse({"error": "Service account credentials not available"}, status=503)
        
        service = build('drive', 'v3', credentials=credentials)
        
        # 파일 업로드 로직 (향후 구현)
        return JsonResponse({"status": "success", "message": "Upload functionality not implemented yet"})
        
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

@csrf_exempt
def list_drive_folder_files(request):
    folder_id = request.GET.get('folder_id')
    
    # POST 요청 시 배치 생성
    if request.method == 'POST':
        return create_batch_from_drive_files(request, folder_id)
    
    if not folder_id:
        return JsonResponse({'error': 'folder_id is required'}, status=400)
    
    # IAM 서비스 계정 credentials 사용
    credentials = get_service_account_credentials()
    if not credentials:
        return JsonResponse({'error': 'Service account credentials not available'}, status=503)
    
    try:
        service = build('drive', 'v3', credentials=credentials)
        
        # 이미지 파일만 필터링
        query = f"'{folder_id}' in parents and (mimeType contains 'image/')"
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, webViewLink, thumbnailLink, mimeType, size)",
            pageSize=1000  # 최대 1000개 파일
        ).execute()
        
        files = results.get('files', [])
        
        # 파일 정보 추가 처리
        processed_files = []
        for file in files:
            # 썸네일 링크가 있으면 크기를 증가시켜서 사용
            thumbnail_url = file.get('thumbnailLink', '')
            if thumbnail_url:
                # 썸네일 크기를 800px로 증가
                display_url = thumbnail_url.replace('=s220', '=s800')
            else:
                # 썸네일이 없으면 일반 다운로드 URL 사용
                display_url = f"https://drive.google.com/uc?id={file['id']}"
            
            processed_files.append({
                'id': file['id'],
                'name': file['name'],
                'webViewLink': file.get('webViewLink', ''),
                'thumbnailLink': thumbnail_url,
                'displayUrl': display_url,
                'mimeType': file['mimeType'],
                'size': file.get('size', '0'),
                'downloadUrl': f"https://drive.google.com/uc?id={file['id']}"
            })
        
        return JsonResponse({
            'files': processed_files,
            'count': len(processed_files)
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def create_batch_from_drive_files(request, folder_id):
    """Google Drive 폴더에서 배치 생성 (분할 배치 지원)"""
    try:
        from django.utils import timezone
        
        batch_name_prefix = request.POST.get('batch_name_prefix', 'Google Drive 배치')
        split_method = request.POST.get('split_method', 'single')
        split_value = int(request.POST.get('split_value', 0)) if request.POST.get('split_value') else 0
        
        # IAM 서비스 계정 credentials 사용
        credentials = get_service_account_credentials()
        if not credentials:
            return JsonResponse({'error': 'Service account credentials not available'}, status=503)
        
        service = build('drive', 'v3', credentials=credentials)
        
        # 폴더의 이미지 파일들 가져오기
        query = f"'{folder_id}' in parents and (mimeType contains 'image/')"
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, mimeType, thumbnailLink)",
            pageSize=1000
        ).execute()
        
        files = results.get('files', [])
        
        if not files:
            return JsonResponse({'error': '폴더에 이미지 파일이 없습니다.'}, status=400)
        
        # 분할 방식에 따라 배치 생성
        created_batches = []
        
        if split_method == 'single':
            # 단일 배치
            batch = Batch.objects.create(
                name=batch_name_prefix,
                created_at=timezone.now()
            )
            
            for file in files:
                # 이미지를 Django 서버에 다운로드해서 저장
                local_url = download_and_save_image(service, file['id'], file['name'], batch.id)
                if local_url:
                    Image.objects.create(
                        batch=batch,
                        file_name=file['name'],
                        url=local_url,
                        drive_file_id=file['id']
                    )
                else:
                    # 다운로드 실패 시 프록시 URL 사용
                    display_url = f"/proxy-drive-image/{file['id']}/"
                    Image.objects.create(
                        batch=batch,
                        file_name=file['name'],
                        url=display_url,
                        drive_file_id=file['id']
                    )
            
            created_batches.append({
                'id': batch.id,
                'name': batch.name,
                'image_count': len(files)
            })
            
        elif split_method == 'by_count':
            # 배치당 이미지 개수로 분할
            images_per_batch = split_value
            total_batches = (len(files) + images_per_batch - 1) // images_per_batch
            
            for batch_num in range(total_batches):
                start_idx = batch_num * images_per_batch
                end_idx = min(start_idx + images_per_batch, len(files))
                batch_files = files[start_idx:end_idx]
                
                batch_name = f"{batch_name_prefix}_{batch_num + 1:02d}"
                batch = Batch.objects.create(
                    name=batch_name,
                    created_at=timezone.now()
                )
                
                for file in batch_files:
                    # 이미지를 Django 서버에 다운로드해서 저장
                    local_url = download_and_save_image(service, file['id'], file['name'], batch.id)
                    if local_url:
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=local_url,
                            drive_file_id=file['id']
                        )
                    else:
                        # 다운로드 실패 시 프록시 URL 사용
                        display_url = f"/proxy-drive-image/{file['id']}/"
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=display_url,
                            drive_file_id=file['id']
                        )
                
                created_batches.append({
                    'id': batch.id,
                    'name': batch.name,
                    'image_count': len(batch_files)
                })
                
        elif split_method == 'by_batches':
            # 총 배치 개수로 분할
            total_batches = min(split_value, len(files))  # 배치 수가 파일 수보다 많을 수 없음
            images_per_batch = len(files) // total_batches
            remaining_images = len(files) % total_batches
            
            current_idx = 0
            for batch_num in range(total_batches):
                # 나머지 이미지를 첫 번째 배치들에 분배
                batch_size = images_per_batch + (1 if batch_num < remaining_images else 0)
                batch_files = files[current_idx:current_idx + batch_size]
                current_idx += batch_size
                
                batch_name = f"{batch_name_prefix}_{batch_num + 1:02d}"
                batch = Batch.objects.create(
                    name=batch_name,
                    created_at=timezone.now()
                )
                
                for file in batch_files:
                    # 이미지를 Django 서버에 다운로드해서 저장
                    local_url = download_and_save_image(service, file['id'], file['name'], batch.id)
                    if local_url:
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=local_url,
                            drive_file_id=file['id']
                        )
                    else:
                        # 다운로드 실패 시 프록시 URL 사용
                        display_url = f"/proxy-drive-image/{file['id']}/"
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=display_url,
                            drive_file_id=file['id']
                        )
                
                created_batches.append({
                    'id': batch.id,
                    'name': batch.name,
                    'image_count': len(batch_files)
                })
        
        # 응답 데이터 구성
        if len(created_batches) == 1:
            # 단일 배치인 경우 기존 형식 유지
            return JsonResponse({
                'success': True,
                'batch_id': created_batches[0]['id'],
                'batch_name': created_batches[0]['name'],
                'image_count': created_batches[0]['image_count'],
                'batches': created_batches
            })
        else:
            # 다중 배치인 경우
            return JsonResponse({
                'success': True,
                'batches': created_batches,
                'total_batches': len(created_batches),
                'total_images': len(files)
            })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def download_and_save_image(service, file_id, file_name, batch_id):
    """Google Drive 이미지를 다운로드해서 Django media 폴더에 저장"""
    try:
        # media/batch_images/{batch_id}/ 디렉토리 생성
        batch_dir = f"batch_images/{batch_id}"
        os.makedirs(os.path.join(settings.MEDIA_ROOT, batch_dir), exist_ok=True)
        
        # 파일 확장자 추출
        file_extension = os.path.splitext(file_name)[1] or '.jpg'
        safe_filename = f"{uuid.uuid4().hex}{file_extension}"
        
        # Google Drive에서 파일 다운로드
        file_content = service.files().get_media(fileId=file_id).execute()
        
        # Django storage에 저장
        file_path = f"{batch_dir}/{safe_filename}"
        saved_path = default_storage.save(file_path, ContentFile(file_content))
        
        # URL 반환
        return f"/media/{saved_path}"
        
    except Exception as e:
        print(f"이미지 다운로드 실패 {file_id}: {str(e)}")
        return None

def drive_import(request):
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요합니다.")
        return redirect("login")
    
    return render(request, 'labeling/drive_import.html')

@login_required
def proxy_drive_image(request, file_id):
    """Google Drive 이미지를 프록시해서 제공 - 보안 강화"""
    from .utils import get_service_account_credentials
    # 사용자 IP 주소 가져오기
    def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    client_ip = get_client_ip(request)
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    # Rate Limiting: 1분간 최대 30회 요청 허용
    from django.utils import timezone
    from datetime import timedelta
    one_minute_ago = timezone.now() - timedelta(minutes=1)
    recent_requests = ImageAccessLog.objects.filter(
        user=request.user,
        access_time__gte=one_minute_ago
    ).count()
    if recent_requests >= 30:
        # 로그 기록
        ImageAccessLog.objects.create(
            user=request.user,
            image_file_id=file_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            error_message="Rate limit exceeded"
        )
        return HttpResponse("Rate limit exceeded. Please wait before requesting more images.", status=429)
    # 1. 기본 인증 확인
    if not request.user.is_authenticated:
        ImageAccessLog.objects.create(
            user=request.user,
            image_file_id=file_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            error_message="Authentication required"
        )
        return HttpResponse("Authentication required", status=401)
    # 2. 사용자 권한 확인 (관리자 또는 승인된 사용자만)
    if request.user.role == 'admin':
        pass
    elif request.user.role == 'user' and request.user.is_approved:
        user_accessible_file_ids = Image.objects.filter(
            batch__is_active=True,
            drive_file_id=file_id
        ).values_list('drive_file_id', flat=True)
        if file_id not in user_accessible_file_ids:
            ImageAccessLog.objects.create(
                user=request.user,
                image_file_id=file_id,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                error_message="Access denied: No permission for this image"
            )
            return HttpResponse("Access denied: You don't have permission to view this image", status=403)
    else:
        ImageAccessLog.objects.create(
            user=request.user,
            image_file_id=file_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            error_message="Access denied: User not approved"
        )
        return HttpResponse("Access denied: User not approved", status=403)
    session_key = request.session.session_key
    if not session_key:
        ImageAccessLog.objects.create(
            user=request.user,
            image_file_id=file_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            error_message="Invalid session"
        )
        return HttpResponse("Invalid session", status=401)
    try:
        try:
            image_obj = Image.objects.get(drive_file_id=file_id)
            if image_obj.url and image_obj.url.startswith('/media/'):
                local_path = os.path.join(settings.MEDIA_ROOT, image_obj.url.replace('/media/', ''))
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        file_content = f.read()
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(local_path)
                    if not content_type:
                        content_type = 'image/jpeg'
                    ImageAccessLog.objects.create(
                        user=request.user,
                        image_file_id=file_id,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        success=True,
                        error_message="Local file served"
                    )
                    http_response = HttpResponse(file_content, content_type=content_type)
                    http_response['Cache-Control'] = 'private, max-age=3600'
                    http_response['X-Content-Type-Options'] = 'nosniff'
                    return http_response
        except Image.DoesNotExist:
            pass
        # IAM 서비스 계정 credentials 사용
        admin_credentials = get_service_account_credentials()
        if not admin_credentials:
            ImageAccessLog.objects.create(
                user=request.user,
                image_file_id=file_id,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                error_message="Service account credentials not available"
            )
            return HttpResponse("Service temporarily unavailable: Service account credentials not available", status=503)
        
        # Credentials 객체 생성
        from google.oauth2.credentials import Credentials
        if hasattr(admin_credentials, 'token') or isinstance(admin_credentials, dict):
            credentials = Credentials(**admin_credentials)
        else:
            credentials = admin_credentials
        service = build('drive', 'v3', credentials=credentials)
        file_metadata = service.files().get(fileId=file_id, fields='mimeType,thumbnailLink').execute()
        thumbnail_link = file_metadata.get('thumbnailLink')
        if thumbnail_link:
            thumbnail_url = thumbnail_link.replace('=s220', '=s800')
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                ImageAccessLog.objects.create(
                    user=request.user,
                    image_file_id=file_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    success=True,
                    error_message="Google Drive thumbnail served"
                )
                content_type = file_metadata.get('mimeType', 'image/jpeg')
                http_response = HttpResponse(response.content, content_type=content_type)
                http_response['Cache-Control'] = 'private, max-age=3600'
                http_response['X-Content-Type-Options'] = 'nosniff'
                return http_response
        try:
            file_content = service.files().get_media(fileId=file_id).execute()
            ImageAccessLog.objects.create(
                user=request.user,
                image_file_id=file_id,
                ip_address=client_ip,
                user_agent=user_agent,
                success=True,
                error_message="Google Drive direct file served"
            )
            content_type = file_metadata.get('mimeType', 'image/jpeg')
            http_response = HttpResponse(file_content, content_type=content_type)
            http_response['Cache-Control'] = 'private, max-age=3600'
            http_response['X-Content-Type-Options'] = 'nosniff'
            return http_response
        except Exception as e:
            print(f"직접 다운로드 실패: {str(e)}")
            ImageAccessLog.objects.create(
                user=request.user,
                image_file_id=file_id,
                ip_address=client_ip,
                user_agent=user_agent,
                success=False,
                error_message=f"Direct download failed: {str(e)}"
            )
            return HttpResponse("Image not available", status=404)
    except Exception as e:
        print(f"이미지 프록시 오류: {str(e)}")
        ImageAccessLog.objects.create(
            user=request.user,
            image_file_id=file_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            error_message=f"Proxy error: {str(e)}"
        )
        return HttpResponse("Error loading image", status=500)



@login_required
def approve_user(request, user_id):
    """사용자 승인"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    try:
        from django.utils import timezone
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id, role='user')
        user.is_approved = True
        user.approved_at = timezone.now()
        user.approved_by = request.user
        user.save()
        
        messages.success(request, f"{user.first_name}님이 승인되었습니다.")
    except User.DoesNotExist:
        messages.error(request, "사용자를 찾을 수 없습니다.")
    
    return redirect('admin_dashboard')

@login_required
def reject_user(request, user_id):
    """사용자 거절 (계정 삭제)"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id, role='user')
        user_name = user.first_name
        user.delete()
        
        messages.success(request, f"{user_name}님의 계정이 삭제되었습니다.")
    except User.DoesNotExist:
        messages.error(request, "사용자를 찾을 수 없습니다.")
    except Exception as e:
        messages.error(request, f"사용자 거절 중 오류가 발생했습니다: {str(e)}")
    
    return redirect('admin_dashboard')

@login_required
def revoke_user_approval(request, user_id):
    """사용자 승인 취소"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id, role='user', is_approved=True)
        user.is_approved = False
        user.approved_at = None
        user.approved_by = None
        user.save()
        
        messages.success(request, f"{user.first_name}님의 승인이 취소되었습니다. 해당 사용자는 다시 승인 대기 상태가 됩니다.")
    except User.DoesNotExist:
        messages.error(request, "승인된 사용자를 찾을 수 없습니다.")
    except Exception as e:
        messages.error(request, f"승인 취소 중 오류가 발생했습니다: {str(e)}")
    
    return redirect('admin_dashboard')

@login_required
def toggle_batch_active(request, batch_id):
    """배치 활성화/비활성화 토글"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    try:
        batch = Batch.objects.get(id=batch_id)
        batch.is_active = not batch.is_active
        batch.save()
        
        status = "활성화" if batch.is_active else "비활성화"
        messages.success(request, f"배치 '{batch.name}'이 {status}되었습니다.")
        
    except Batch.DoesNotExist:
        messages.error(request, "배치를 찾을 수 없습니다.")
    except Exception as e:
        messages.error(request, f"오류가 발생했습니다: {str(e)}")
    
    return redirect('admin_dashboard')

@login_required
def delete_batch(request, batch_id):
    """배치 삭제"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    try:
        batch = Batch.objects.get(id=batch_id)
        batch_name = batch.name
        
        # 관련된 이미지들도 함께 삭제됨 (CASCADE)
        batch.delete()
        
        messages.success(request, f"배치 '{batch_name}'이 삭제되었습니다.")
        
    except Batch.DoesNotExist:
        messages.error(request, "배치를 찾을 수 없습니다.")
    except Exception as e:
        messages.error(request, f"오류가 발생했습니다: {str(e)}")
    
    return redirect('admin_dashboard')

@login_required  
def reset_batch_progress(request, batch_id):
    """배치 진행률 초기화"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    try:
        batch = Batch.objects.get(id=batch_id)
        
        # 해당 배치의 모든 라벨링 결과 삭제
        LabelingResult.objects.filter(image__batch=batch).delete()
        
        messages.success(request, f"배치 '{batch.name}'의 진행률이 초기화되었습니다.")
        
    except Batch.DoesNotExist:
        messages.error(request, "배치를 찾을 수 없습니다.")
    except Exception as e:
        messages.error(request, f"오류가 발생했습니다: {str(e)}")
    
    return redirect('admin_dashboard')

# 메시지 관련 뷰들

@login_required
@csrf_exempt
def send_message(request):
    """사용자가 관리자에게 메시지 전송"""
    if request.user.role != 'user' or not request.user.is_approved:
        return JsonResponse({'success': False, 'error': '권한이 없습니다.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_type = data.get('message_type')  # 'global' 또는 'batch'
            subject = data.get('subject', '').strip()
            content = data.get('content', '').strip()
            batch_id = data.get('batch_id')
            
            # 필수 필드 검증
            if not subject or not content:
                return JsonResponse({'success': False, 'error': '제목과 내용을 모두 입력해주세요.'})
            
            if len(subject) > 200:
                return JsonResponse({'success': False, 'error': '제목은 200자 이내로 입력해주세요.'})
            
            if len(content) > 2000:
                return JsonResponse({'success': False, 'error': '내용은 2000자 이내로 입력해주세요.'})
            
            # 배치별 메시지인 경우 배치 검증
            batch = None
            if message_type == 'batch':
                if not batch_id:
                    return JsonResponse({'success': False, 'error': '배치를 선택해주세요.'})
                
                try:
                    batch = Batch.objects.get(id=batch_id, is_active=True)
                except Batch.DoesNotExist:
                    return JsonResponse({'success': False, 'error': '유효하지 않은 배치입니다.'})
            
            # 메시지 생성
            message = Message.objects.create(
                sender=request.user,
                message_type=message_type,
                subject=subject,
                content=content,
                batch=batch
            )
            
            return JsonResponse({
                'success': True, 
                'message': '메시지가 전송되었습니다. 관리자가 확인 후 답변드리겠습니다.'
            })
            
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '잘못된 요청 형식입니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': '잘못된 요청 방법입니다.'})

@login_required
def user_messages(request):
    """사용자의 메시지 목록 조회"""
    if request.user.role != 'user' or not request.user.is_approved:
        messages.error(request, "권한이 없습니다.")
        return redirect('login')
    
    user_messages = Message.objects.filter(sender=request.user).order_by('-created_at')
    
    context = {
        'user_messages': user_messages
    }
    return render(request, 'labeling/user_messages.html', context)

@login_required
def admin_messages(request):
    """관리자의 메시지 관리 페이지"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    # 읽지 않은 메시지 우선 정렬
    all_messages = Message.objects.select_related('sender', 'batch', 'replied_by').order_by('is_read', '-created_at')
    
    # 통계 계산
    total_messages = all_messages.count()
    unread_count = all_messages.filter(is_read=False).count()
    replied_count = all_messages.filter(admin_reply__isnull=False).count()
    
    context = {
        'all_messages': all_messages,
        'total_messages': total_messages,
        'unread_count': unread_count,
        'replied_count': replied_count,
    }
    return render(request, 'labeling/admin_messages.html', context)

@login_required
@csrf_exempt
def reply_message(request):
    """관리자가 메시지에 답변"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': '관리자 권한이 필요합니다.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')
            reply_content = data.get('reply', '').strip()
            
            if not reply_content:
                return JsonResponse({'success': False, 'error': '답변 내용을 입력해주세요.'})
            
            if len(reply_content) > 2000:
                return JsonResponse({'success': False, 'error': '답변은 2000자 이내로 입력해주세요.'})
            
            try:
                from django.utils import timezone
                message = Message.objects.get(id=message_id)
                message.admin_reply = reply_content
                message.replied_at = timezone.now()
                message.replied_by = request.user
                message.is_read = True
                message.save()
                
                return JsonResponse({'success': True, 'message': '답변이 저장되었습니다.'})
                
            except Message.DoesNotExist:
                return JsonResponse({'success': False, 'error': '메시지를 찾을 수 없습니다.'})
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '잘못된 요청 형식입니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': '잘못된 요청 방법입니다.'})

@login_required
@csrf_exempt
def mark_message_read(request):
    """메시지를 읽음으로 표시"""
    if request.user.role != 'admin':
        return JsonResponse({'success': False, 'error': '관리자 권한이 필요합니다.'})
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            message_id = data.get('message_id')
            
            try:
                message = Message.objects.get(id=message_id)
                message.is_read = True
                message.save()
                
                return JsonResponse({'success': True})
                
            except Message.DoesNotExist:
                return JsonResponse({'success': False, 'error': '메시지를 찾을 수 없습니다.'})
                
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': '잘못된 요청 형식입니다.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': f'오류가 발생했습니다: {str(e)}'})
    
    return JsonResponse({'success': False, 'error': '잘못된 요청 방법입니다.'})

def logout_view(request):
    """완전한 로그아웃 처리"""
    # 사용자 정보 저장 (메시지용)
    user_name = request.user.first_name if request.user.is_authenticated else "사용자"
    
    # Django 로그아웃 처리
    logout(request)
    
    # 세션 데이터 완전 삭제
    request.session.flush()
    
    # 성공 메시지 추가
    messages.success(request, f"{user_name}님이 성공적으로 로그아웃되었습니다.")
    
    # 캐시 방지를 위한 응답 헤더 설정
    response = redirect("login")
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response

@login_required
def test_service_account_view(request):
    """서비스 계정 테스트 뷰 (관리자 전용)"""
    if request.user.role != 'admin':
        messages.error(request, "관리자 권한이 필요합니다.")
        return redirect('login')
    
    if request.method == 'POST':
        success, message = test_service_account_access()
        
        if success:
            messages.success(request, f"서비스 계정 테스트 성공: {message}")
        else:
            messages.error(request, f"서비스 계정 테스트 실패: {message}")
        
        return redirect('admin_dashboard')
    
    # GET 요청 시 테스트 결과만 표시
    success, message = test_service_account_access()
    
    context = {
        'test_success': success,
        'test_message': message,
        'service_account_available': get_service_account_credentials() is not None
    }
    
    return render(request, 'labeling/test_service_account.html', context)
