# labeling/urls.py
from django.urls import path
from django.shortcuts import redirect
from . import views

def root_redirect(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    else:
        return redirect('login')

urlpatterns = [
    path('', root_redirect, name='root'),
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('labeling/<int:batch_id>/', views.labeling, name='labeling'),
    path('api/labeling/save-progress', views.save_progress, name='save_progress'),
    path('api/labeling/save-label', views.save_label, name='save_label'),
    path('api/labeling/load-progress/<int:user_id>/<int:batch_id>/', views.load_progress, name='load_progress'),
    path('api/labeling/batches/<int:user_id>/', views.get_batches, name='get_batches'),
    path('api/validate-user', views.validate_user, name='validate_user'),

    path('waiting/', views.waiting, name='waiting'),
    # 사용자 승인 관련
    path('approve-user/<int:user_id>/', views.approve_user, name='approve_user'),
    path('reject-user/<int:user_id>/', views.reject_user, name='reject_user'),
    path('revoke-user/<int:user_id>/', views.revoke_user_approval, name='revoke_user_approval'),
    # 배치 관리
    path('batch/<int:batch_id>/toggle/', views.toggle_batch_active, name='toggle_batch_active'),
    path('batch/<int:batch_id>/delete/', views.delete_batch, name='delete_batch'),
    path('batch/<int:batch_id>/reset/', views.reset_batch_progress, name='reset_batch_progress'),

    path('drive-folder-files/', views.list_drive_folder_files, name='list_drive_folder_files'),
    path('drive-import/', views.drive_import, name='drive_import'),
    path('proxy-drive-image/<str:file_id>/', views.proxy_drive_image, name='proxy_drive_image'),
    path('create-batch/<str:folder_id>/', views.create_batch_from_drive_files, name='create_batch_from_drive_files'),
    # 메시지 관련
    path('api/send-message/', views.send_message, name='send_message'),
    path('my-messages/', views.user_messages, name='user_messages'),
    path('admin-messages/', views.admin_messages, name='admin_messages'),
    path('api/reply-message/', views.reply_message, name='reply_message'),
    path('api/mark-message-read/', views.mark_message_read, name='mark_message_read'),
    # 서비스 계정 테스트
    path('test-service-account/', views.test_service_account_view, name='test_service_account'),
]