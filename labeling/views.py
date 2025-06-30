#!/usr/bin/env python
import os
import json
from django.shortcuts import render, redirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Batch, Image, Label, LabelingResult, ImageAccessLog, Message
from .thumbnail_utils import get_batch_thumbnail_url, validate_batch_thumbnails, check_thumbnail_system_health
from django.views.decorators.csrf import csrf_exempt
from django.db import models
import json

from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from .utils import get_google_oauth_config
from google_auth_oauthlib.flow import Flow
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from googleapiclient.http import MediaFileUpload
import requests
import io
import uuid
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile

# 개발 환경에서 HTTPS 요구사항 우회 (OAuth 2.0 insecure transport 해결)
# HTTPS를 사용할 때는 이 설정을 주석 처리하세요
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# config 불러오기
google_config = get_google_oauth_config()
GOOGLE_CLIENT_ID = google_config["client_id"]
GOOGLE_CLIENT_SECRET = google_config["client_secret"]

# 로그인 관련 뷰
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

def waiting(request):
    """승인 대기 페이지"""
    return render(request, 'labeling/waiting.html')

@login_required
def admin_dashboard(request):
    if request.user.role != 'admin':
        return redirect('dashboard')
    
    # Google Drive 인증 상태 확인
    drive_credentials_available = 'drive_credentials' in request.session
    
    batches = Batch.objects.prefetch_related('images').all().order_by('-created_at')
    
    # 승인 대기 중인 사용자들
    from django.contrib.auth import get_user_model
    User = get_user_model()
    pending_users = User.objects.filter(role='user', is_approved=False).order_by('-date_joined')
    
    # 배치 상태 통계 추가
    all_batches_count = Batch.objects.count()
    active_batches_count = batches.count()
    inactive_batches_count = Batch.objects.filter(is_active=False).count()

    # 배치별 썸네일 정보 추가 (안전한 썸네일 시스템 사용)
    batches_with_info = []
    for batch in batches:
        # 안전한 썸네일 URL 생성
        thumbnail_url = get_batch_thumbnail_url(batch)
        
        # 배치별 전체 진행률 계산
        total_images = batch.images.count()
        labeled_count = LabelingResult.objects.filter(image__batch=batch).values('image').distinct().count()
        progress_percentage = (labeled_count / total_images * 100) if total_images > 0 else 0
        
        batches_with_info.append({
            'batch': batch,
            'thumbnail_url': thumbnail_url,
            'total_images': total_images,
            'labeled_count': labeled_count,
            'progress_percentage': round(progress_percentage, 1)
        })
    
    # 사용자별 진행률 통계
    user_stats = []
    approved_users = User.objects.filter(role='user', is_approved=True)
    
    for user in approved_users:
        # 각 배치별 사용자 진행률
        user_batch_progress = []
        total_assigned = 0
        total_completed = 0
        
        for batch in batches:
            if batch.is_active:  # 활성 배치만 계산
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
    
    # 보안 모니터링 통계
    from django.utils import timezone
    from datetime import timedelta
    
    # 최근 24시간 이미지 접근 통계
    yesterday = timezone.now() - timedelta(days=1)
    recent_access_logs = ImageAccessLog.objects.filter(access_time__gte=yesterday)
    
    security_stats = {
        'total_requests': recent_access_logs.count(),
        'successful_requests': recent_access_logs.filter(success=True).count(),
        'failed_requests': recent_access_logs.filter(success=False).count(),
        'rate_limit_violations': recent_access_logs.filter(error_message__contains='Rate limit').count(),
        'unauthorized_attempts': recent_access_logs.filter(error_message__contains='Access denied').count(),
        'top_users': recent_access_logs.values('user__email').annotate(
            request_count=models.Count('id')
        ).order_by('-request_count')[:5],
        'recent_failures': recent_access_logs.filter(success=False).order_by('-access_time')[:10]
    }
    
    # 메시지 통계
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
        'batch_stats': {
            'total_batches': all_batches_count,
            'active_batches': active_batches_count,
            'inactive_batches': inactive_batches_count
        },
        'drive_credentials_available': drive_credentials_available
    }
    return render(request, 'labeling/admin_dashboard.html', context)

def dashboard(request):
    # 인증 확인 (자동 리다이렉트 방지)
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요합니다.")
        return redirect("login")
    
    # 관리자는 관리자 대시보드로 리다이렉트
    if request.user.role == 'admin':
        return redirect('admin_dashboard')
    
    # 승인되지 않은 사용자는 대기 페이지로 리다이렉트
    if not request.user.is_approved:
        return redirect('waiting')
    
    # Google Drive 인증 상태 확인
    drive_credentials_available = 'drive_credentials' in request.session
    
    # 활성화된 배치만 표시
    batches = Batch.objects.filter(is_active=True)
    
    batch_data = []
    total_images = 0
    completed_images = 0
    
    for batch in batches:
        batch_images = batch.images.all()
        batch_total = batch_images.count()
        
        # 라벨링 완료된 이미지 수 계산
        batch_completed = LabelingResult.objects.filter(
            image__batch=batch,
            user=request.user
        ).values('image').distinct().count()
        
        progress_percentage = (batch_completed / batch_total * 100) if batch_total > 0 else 0
        is_completed = batch_completed >= batch_total
        
        # 안전한 썸네일 URL 생성 (전용 유틸리티 사용)
        thumbnail_url = get_batch_thumbnail_url(batch)
        
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
    
    # 배치 상태 정보 추가
    all_batches = Batch.objects.all()
    inactive_batches = Batch.objects.filter(is_active=False)
    
    context = {
        "batches": batch_data,
        "batches_json": batch_data,
        "total_images": total_images,
        "completed_images": completed_images,
        "overall_progress": overall_progress,
        "google_user_info": request.session.get('google_user_info', {}),
        "user_role": request.user.role,
        "batch_info": {
            "has_active_batches": batches.exists(),
            "total_batches": all_batches.count(),
            "inactive_batches": inactive_batches.count(),
            "inactive_batch_names": [batch.name for batch in inactive_batches[:3]]  # 최대 3개만 표시
        },
        "drive_credentials_available": drive_credentials_available
    }
    
    return render(request, "labeling/dashboard.html", context)

def labeling(request, batch_id):
    # 인증 확인 (자동 리다이렉트 방지)
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
        
        return render(request, "labeling/labeling.html", context)
        
    except Batch.DoesNotExist:
        messages.error(request, "배치를 찾을 수 없습니다.")
        return redirect("dashboard")
    except Exception as e:
        messages.error(request, f"오류가 발생했습니다: {str(e)}")
        return redirect("dashboard")

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

def google_user_login_start(request):
    """Google 사용자 로그인 시작 (Drive 권한 없음)"""
    try:
        print(f"[INFO] Google 사용자 로그인 시작 - Client ID: {GOOGLE_CLIENT_ID[:20]}...")
        
        # OAuth 세션 상태 클리어
        if 'google_oauth_state' in request.session:
            del request.session['google_oauth_state']
        if 'drive_oauth_state' in request.session:
            del request.session['drive_oauth_state']
        request.session.modified = True
        
        # 동적 리디렉션 URI 생성 (현재 도메인 기반)
        redirect_uri = request.build_absolute_uri('/google-user-auth-callback/')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            prompt='consent'
        )
        
        request.session['google_oauth_state'] = state
        request.session['login_type'] = 'user'
        return redirect(authorization_url)
        
    except Exception as e:
        print(f"[ERROR] Google 사용자 로그인 오류: {str(e)}")
        messages.error(request, f"Google 사용자 로그인 시작 실패: {str(e)}")
        return redirect('login')

def google_admin_login_start(request):
    """Google 관리자 로그인 시작 (Drive 권한 포함)"""
    try:
        print(f"[INFO] Google 관리자 로그인 시작 - Client ID: {GOOGLE_CLIENT_ID[:20]}...")
        
        # OAuth 세션 상태 클리어
        if 'google_oauth_state' in request.session:
            del request.session['google_oauth_state']
        if 'drive_oauth_state' in request.session:
            del request.session['drive_oauth_state']
        request.session.modified = True
        
        # 동적 리디렉션 URI 생성 (현재 도메인 기반)
        redirect_uri = request.build_absolute_uri('/google-admin-auth-callback/')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ],
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        request.session['google_oauth_state'] = state
        request.session['login_type'] = 'admin'
        return redirect(authorization_url)
        
    except Exception as e:
        print(f"[ERROR] Google 관리자 로그인 오류: {str(e)}")
        messages.error(request, f"Google 관리자 로그인 시작 실패: {str(e)}")
        return redirect('login')

def google_drive_auth_start(request):
    """Google Drive 인증 시작 (기존 로그인된 사용자용)"""
    if not request.user.is_authenticated:
        messages.error(request, "먼저 로그인해주세요.")
        return redirect('login')
        
    try:
        # 동적 리디렉션 URI 생성 (현재 도메인 기반)
        redirect_uri = request.build_absolute_uri('/google-drive-auth-callback/')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ],
            redirect_uri=redirect_uri
        )
        
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
        )
        
        request.session['drive_oauth_state'] = state
        return redirect(authorization_url)
        
    except Exception as e:
        messages.error(request, f"Google Drive 인증 시작 실패: {str(e)}")
        return redirect('drive_import')

def google_user_auth_callback(request):
    """Google 사용자 로그인 콜백 처리"""
    try:
        if 'google_oauth_state' not in request.session:
            messages.error(request, "인증 상태가 올바르지 않습니다. 다시 시도해주세요.")
            return redirect('login')
        
        # 동적 리디렉션 URI 생성 (현재 도메인 기반)
        redirect_uri = request.build_absolute_uri('/google-user-auth-callback/')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email", 
                "https://www.googleapis.com/auth/userinfo.profile"
            ],
            state=request.session['google_oauth_state'],
            redirect_uri=redirect_uri
        )
        
        # 인증 토큰 가져오기
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        
        credentials = flow.credentials
        
        # 사용자 정보 가져오기 (시간 동기화 문제 대응)
        import time
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                id_info = id_token.verify_oauth2_token(
                    credentials.id_token, google_requests.Request(), GOOGLE_CLIENT_ID)
                break
            except ValueError as e:
                if "Token used too early" in str(e) and attempt < max_retries - 1:
                    print(f"[RETRY] 토큰 시간 동기화 문제 감지, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise e
        
        # 사용자 생성 또는 로그인
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        email = id_info.get('email')
        name = id_info.get('name')
        google_id = id_info.get('sub')
        
        # 사용자 찾기 또는 생성
        user, created = User.objects.get_or_create(
            google_id=google_id,
            defaults={
                'username': f"user_{google_id}",
                'email': email,
                'first_name': name,
                'role': 'user',
                'is_active': True,
                'is_approved': False  # 관리자 승인 대기
            }
        )
        
        if created:
            messages.info(request, f"새 계정이 생성되었습니다. 관리자 승인을 기다리고 있습니다.")
        elif not user.is_approved:
            messages.warning(request, "계정이 아직 승인되지 않았습니다. 관리자 승인을 기다려주세요.")
        else:
            messages.success(request, f"환영합니다, {name}님!")
        
        # 승인된 사용자만 로그인 처리
        if user.is_approved:
            login(request, user)
            
            # 사용자 정보 저장
            request.session['google_user_info'] = {
                'email': email,
                'name': name,
                'picture': id_info.get('picture', ''),
                'google_id': google_id
            }
            
            # 인증 상태 정리
            del request.session['google_oauth_state']
            return redirect('dashboard')
        else:
            # 승인 대기 페이지로 이동
            del request.session['google_oauth_state']
            return redirect('waiting')
        
    except Exception as e:
        messages.error(request, f"Google 사용자 로그인 실패: {str(e)}")
        return redirect('login')

def google_admin_auth_callback(request):
    """Google 관리자 로그인 콜백 처리"""
    try:
        if 'google_oauth_state' not in request.session:
            messages.error(request, "인증 상태가 올바르지 않습니다. 다시 시도해주세요.")
            return redirect('login')
        
        # 동적 리디렉션 URI 생성 (현재 도메인 기반)
        redirect_uri = request.build_absolute_uri('/google-admin-auth-callback/')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "openid",
                "https://www.googleapis.com/auth/userinfo.email", 
                "https://www.googleapis.com/auth/userinfo.profile",
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ],
            state=request.session['google_oauth_state'],
            redirect_uri=redirect_uri
        )
        
        # 인증 토큰 가져오기
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        
        credentials = flow.credentials
        
        # 사용자 정보 가져오기 (시간 동기화 문제 대응)
        import time
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                id_info = id_token.verify_oauth2_token(
                    credentials.id_token, google_requests.Request(), GOOGLE_CLIENT_ID)
                break
            except ValueError as e:
                if "Token used too early" in str(e) and attempt < max_retries - 1:
                    print(f"[RETRY] 토큰 시간 동기화 문제 감지, {retry_delay}초 후 재시도... (시도 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    raise e
        
        # 관리자 화이트리스트 확인
        from django.conf import settings
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        email = id_info.get('email')
        name = id_info.get('name')
        google_id = id_info.get('sub')
        
        if email not in settings.ADMIN_WHITELIST:
            messages.error(request, "관리자 권한이 없습니다.")
            return redirect('login')
        
        # 관리자 사용자 찾기 또는 생성
        user, created = User.objects.get_or_create(
            google_id=google_id,
            defaults={
                'username': f"admin_{google_id}",
                'email': email,
                'first_name': name,
                'role': 'admin',
                'is_active': True,
                'is_approved': True,  # 관리자는 자동 승인
                'is_staff': True,
                'is_superuser': True
            }
        )
        
        if created:
            messages.success(request, f"관리자 계정이 생성되었습니다. 환영합니다, {name}님!")
        else:
            messages.success(request, f"환영합니다, {name} 관리자님!")
        
        # Django 로그인 처리
        login(request, user)
        
        # Google Drive 인증 정보 저장
        request.session['drive_credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # 사용자 정보 저장
        request.session['google_user_info'] = {
            'email': email,
            'name': name,
            'picture': id_info.get('picture', ''),
            'google_id': google_id
        }
        
        # 인증 상태 정리
        del request.session['google_oauth_state']
        
        return redirect('admin_dashboard')
        
    except Exception as e:
        messages.error(request, f"Google 관리자 로그인 실패: {str(e)}")
        return redirect('login')

def google_drive_auth_callback(request):
    """Google Drive 인증 콜백 처리 (기존 로그인된 사용자용)"""
    try:
        if 'drive_oauth_state' not in request.session:
            messages.error(request, "인증 상태가 올바르지 않습니다. 다시 시도해주세요.")
            return redirect('drive_import')
        
        # 동적 리디렉션 URI 생성 (현재 도메인 기반)
        redirect_uri = request.build_absolute_uri('/google-drive-auth-callback/')
        
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [redirect_uri]
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/drive.readonly",
                "https://www.googleapis.com/auth/drive.metadata.readonly"
            ],
            state=request.session['drive_oauth_state'],
            redirect_uri=redirect_uri
        )
        
        # 인증 토큰 가져오기
        flow.fetch_token(authorization_response=request.build_absolute_uri())
        
        credentials = flow.credentials
        
        # 세션에 인증 정보 저장
        request.session['drive_credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # 인증 상태 정리
        del request.session['drive_oauth_state']
        
        messages.success(request, "Google Drive 인증이 완료되었습니다!")
        return redirect('drive_import')
        
    except Exception as e:
        messages.error(request, f"Google Drive 인증 실패: {str(e)}")
        return redirect('drive_import')

def upload_to_drive(request):
    """Google Drive에 파일 업로드 (향후 확장용)"""
    if 'drive_credentials' not in request.session:
        return redirect('google_drive_auth_start')
    
    try:
        credentials = Credentials(**request.session['drive_credentials'])
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
    
    if 'drive_credentials' not in request.session:
        return JsonResponse({'error': 'Not authenticated'}, status=401)
    
    try:
        credentials = Credentials(**request.session['drive_credentials'])
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
    """Google Drive 폴더에서 배치 생성 (분할 배치 지원 + 랜덤 샘플링)"""
    try:
        from django.utils import timezone
        import random
        
        batch_name_prefix = request.POST.get('batch_name_prefix', 'Google Drive 배치')
        split_method = request.POST.get('split_method', 'single')
        split_value = int(request.POST.get('split_value', 0)) if request.POST.get('split_value') else 0
        
        # 테스트 모드 파라미터
        test_mode = request.POST.get('test_mode', 'false').lower() == 'true'
        random_seed = int(request.POST.get('random_seed', 42)) if request.POST.get('random_seed') else 42
        max_images = int(request.POST.get('max_images', 50)) if request.POST.get('max_images') else 50
        
        if 'drive_credentials' not in request.session:
            return JsonResponse({'error': 'Not authenticated'}, status=401)
        
        credentials = Credentials(**request.session['drive_credentials'])
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
        
        # 테스트 모드: 랜덤 샘플링
        if test_mode:
            print(f"[INFO] 테스트 모드 활성화 - Seed: {random_seed}, 최대 이미지: {max_images}")
            random.seed(random_seed)  # 재현 가능한 랜덤 시드 설정
            
            if len(files) > max_images:
                files = random.sample(files, max_images)
                print(f"[INFO] 랜덤 샘플링: {len(files)}개 이미지 선택됨 (전체 {len(results.get('files', []))}개 중)")
                
                # 테스트 모드 배치명에 표시
                if batch_name_prefix == 'Google Drive 배치':
                    batch_name_prefix = f'테스트_{batch_name_prefix}_seed{random_seed}'
                else:
                    batch_name_prefix = f'테스트_{batch_name_prefix}_seed{random_seed}'
            else:
                print(f"[INFO] 폴더 이미지 수({len(files)})가 최대값({max_images})보다 적어 전체 사용")
        
        # 분할 방식에 따라 배치 생성
        created_batches = []
        
        if split_method == 'single':
            # 단일 배치
            batch = Batch.objects.create(
                name=batch_name_prefix,
                created_at=timezone.now()
            )
            
            for file in files:
                # 프록시 URL 생성 (Render 호환)
                proxy_url = download_and_save_image(service, file['id'], file['name'], batch.id)
                if proxy_url:
                    Image.objects.create(
                        batch=batch,
                        file_name=file['name'],
                        url=proxy_url,
                        drive_file_id=file['id']
                    )
                else:
                    # 프록시 URL 생성 실패 시 기본 프록시 URL 사용
                    fallback_url = f"/proxy/drive/{file['id']}/"
                    Image.objects.create(
                        batch=batch,
                        file_name=file['name'],
                        url=fallback_url,
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
                    # 프록시 URL 생성 (Render 호환)
                    proxy_url = download_and_save_image(service, file['id'], file['name'], batch.id)
                    if proxy_url:
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=proxy_url,
                            drive_file_id=file['id']
                        )
                    else:
                        # 프록시 URL 생성 실패 시 기본 프록시 URL 사용
                        fallback_url = f"/proxy/drive/{file['id']}/"
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=fallback_url,
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
                    # 프록시 URL 생성 (Render 호환)
                    proxy_url = download_and_save_image(service, file['id'], file['name'], batch.id)
                    if proxy_url:
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=proxy_url,
                            drive_file_id=file['id']
                        )
                    else:
                        # 프록시 URL 생성 실패 시 기본 프록시 URL 사용
                        fallback_url = f"/proxy/drive/{file['id']}/"
                        Image.objects.create(
                            batch=batch,
                            file_name=file['name'],
                            url=fallback_url,
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
    """Google Drive 이미지를 프록시 URL로 반환 (Render 호환)"""
    try:
        # Render는 읽기 전용 파일 시스템이므로 프록시 방식 사용
        # 파일 존재 여부 확인 (선택적)
        try:
            file_metadata = service.files().get(fileId=file_id, fields='id,name,mimeType').execute()
            print(f"[INFO] 프록시 이미지 설정: {file_name} (ID: {file_id})")
        except Exception as e:
            print(f"[WARNING] 파일 메타데이터 확인 실패 {file_id}: {str(e)}")
        
        # 프록시 URL 반환 (다운로드 없이 직접 서빙)
        proxy_url = f"/proxy/drive/{file_id}/"
        return proxy_url
        
    except Exception as e:
        print(f"[ERROR] 프록시 URL 생성 실패 {file_id}: {str(e)}")
        return None

def drive_import(request):
    if not request.user.is_authenticated:
        messages.error(request, "로그인이 필요합니다.")
        return redirect("login")
    
    return render(request, 'labeling/drive_import.html')

@login_required
def proxy_drive_image(request, file_id):
    """Google Drive 이미지를 프록시해서 제공 - 보안 강화"""
    
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
        # 관리자는 모든 이미지 접근 가능
        pass
    elif request.user.role == 'user' and request.user.is_approved:
        # 승인된 사용자는 자신이 접근 가능한 배치의 이미지만 접근 가능
        user_accessible_file_ids = Image.objects.filter(
            batch__is_active=True,  # 활성 배치만
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
        # 승인되지 않은 사용자는 접근 불가
        ImageAccessLog.objects.create(
            user=request.user,
            image_file_id=file_id,
            ip_address=client_ip,
            user_agent=user_agent,
            success=False,
            error_message="Access denied: User not approved"
        )
        return HttpResponse("Access denied: User not approved", status=403)
    
    # 3. 세션 하이재킹 방지 - 추가 보안 검증
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
        # 4. 먼저 로컬에 다운로드된 이미지가 있는지 확인
        try:
            # 중복 Image 객체 처리: get() 대신 filter().first() 사용
            image_obj = Image.objects.filter(drive_file_id=file_id).first()
            if not image_obj:
                raise Image.DoesNotExist
            if image_obj.url and image_obj.url.startswith('/media/'):
                # 로컬 파일이 존재하는지 확인
                local_path = os.path.join(settings.MEDIA_ROOT, image_obj.url.replace('/media/', ''))
                if os.path.exists(local_path):
                    with open(local_path, 'rb') as f:
                        file_content = f.read()
                    
                    # MIME 타입 추정
                    import mimetypes
                    content_type, _ = mimetypes.guess_type(local_path)
                    if not content_type:
                        content_type = 'image/jpeg'
                    
                    # 성공 로그 기록
                    ImageAccessLog.objects.create(
                        user=request.user,
                        image_file_id=file_id,
                        ip_address=client_ip,
                        user_agent=user_agent,
                        success=True,
                        error_message="Local file served"
                    )
                    
                    http_response = HttpResponse(file_content, content_type=content_type)
                    http_response['Cache-Control'] = 'private, max-age=3600'  # 1시간 캐시
                    http_response['X-Content-Type-Options'] = 'nosniff'  # 보안 헤더
                    return http_response
        except Image.DoesNotExist:
            pass
        
        # 5. 로컬 파일이 없으면 Google Drive에서 프록시 (관리자 크레덴셜 필요)
        admin_credentials = None
        
        # 현재 사용자가 관리자이고 drive_credentials가 있으면 사용
        if request.user.role == 'admin' and 'drive_credentials' in request.session:
            admin_credentials = request.session['drive_credentials']
        else:
            # 일반 사용자의 경우, 시스템 전체에서 관리자 크레덴셜 찾기
            # (실제 프로덕션에서는 Redis나 별도 저장소 사용 권장)
            admin_credentials = get_system_admin_credentials()
            
            if not admin_credentials:
                ImageAccessLog.objects.create(
                    user=request.user,
                    image_file_id=file_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    success=False,
                    error_message="Admin credentials not found"
                )
                return HttpResponse("Service temporarily unavailable: Admin credentials not found", status=503)
        
        credentials = Credentials(**admin_credentials)
        service = build('drive', 'v3', credentials=credentials)
        
        # 파일 메타데이터 가져오기
        file_metadata = service.files().get(fileId=file_id, fields='mimeType,thumbnailLink').execute()
        
        # 썸네일 링크가 있으면 사용
        thumbnail_link = file_metadata.get('thumbnailLink')
        if thumbnail_link:
            # 썸네일 크기를 800px로 증가
            thumbnail_url = thumbnail_link.replace('=s220', '=s800')
            
            # 썸네일 이미지 다운로드
            response = requests.get(thumbnail_url)
            if response.status_code == 200:
                # 성공 로그 기록
                ImageAccessLog.objects.create(
                    user=request.user,
                    image_file_id=file_id,
                    ip_address=client_ip,
                    user_agent=user_agent,
                    success=True,
                    error_message="Google Drive thumbnail served"
                )
                
                # 적절한 Content-Type 설정
                content_type = file_metadata.get('mimeType', 'image/jpeg')
                http_response = HttpResponse(response.content, content_type=content_type)
                http_response['Cache-Control'] = 'private, max-age=3600'  # 1시간 캐시
                http_response['X-Content-Type-Options'] = 'nosniff'  # 보안 헤더
                return http_response
        
        # 썸네일이 없으면 파일 직접 다운로드 시도
        try:
            file_content = service.files().get_media(fileId=file_id).execute()
            
            # 성공 로그 기록
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
            http_response['Cache-Control'] = 'private, max-age=3600'  # 1시간 캐시
            http_response['X-Content-Type-Options'] = 'nosniff'  # 보안 헤더
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

def get_system_admin_credentials():
    """시스템에서 관리자 크레덴셜을 찾는 함수 (간단한 구현)"""
    # 실제 프로덕션에서는 Redis, 데이터베이스, 또는 안전한 저장소 사용
    
    # 임시: 현재 활성 세션에서 관리자 크레덴셜 찾기
    from django.contrib.sessions.models import Session
    from django.utils import timezone
    import pickle
    
    try:
        # 최근 24시간 내 세션 중에서 drive_credentials가 있는 것 찾기
        recent_sessions = Session.objects.filter(
            expire_date__gt=timezone.now()
        ).order_by('-expire_date')[:50]  # 최근 50개 세션만 확인
        
        for session in recent_sessions:
            try:
                session_data = session.get_decoded()
                if 'drive_credentials' in session_data:
                    # 해당 세션의 사용자가 관리자인지 확인
                    user_id = session_data.get('_auth_user_id')
                    if user_id:
                        from django.contrib.auth import get_user_model
                        User = get_user_model()
                        try:
                            user = User.objects.get(id=user_id, role='admin')
                            return session_data['drive_credentials']
                        except User.DoesNotExist:
                            continue
            except:
                continue
        
        return None
    except Exception as e:
        print(f"관리자 크레덴셜 찾기 오류: {str(e)}")
        return None

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
