import os
import json
from django.conf import settings
from google.oauth2 import service_account
from googleapiclient.discovery import build

# 서비스 계정 키 파일 설정 (개발 환경: 로컬 파일, 프로덕션: 환경 변수)
def setup_service_account_key():
    """서비스 계정 키 파일을 설정합니다."""
    key_path_env = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_PATH')
    key_json_env = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_JSON')
    
    # 환경 변수에 JSON이 있으면 파일로 저장 (프로덕션 환경)
    if key_json_env and key_path_env:
        # 절대 경로로 변환
        if not os.path.isabs(key_path_env):
            key_path = os.path.join(settings.BASE_DIR, key_path_env)
        else:
            key_path = key_path_env
        
        # 파일이 없으면 생성
        if not os.path.exists(key_path):
            try:
                with open(key_path, 'w') as f:
                    f.write(key_json_env)
                print(f"[INFO] 서비스 계정 키 파일을 환경 변수에서 생성: {key_path}")
            except Exception as e:
                print(f"[ERROR] 서비스 계정 키 파일 생성 실패: {str(e)}")
    
    # 개발 환경에서는 기본 키 파일 경로 사용
    elif not key_path_env:
        default_key_path = os.path.join(settings.BASE_DIR, 'image-labeling-test-464107-ae81484b9900.json')
        if os.path.exists(default_key_path):
            os.environ['GOOGLE_SERVICE_ACCOUNT_KEY_PATH'] = default_key_path
            print(f"[INFO] 기본 서비스 계정 키 파일 사용: {default_key_path}")

# 앱 시작 시 키 파일 설정
setup_service_account_key()



def get_service_account_credentials():
    """
    서비스 계정 크레덴셜을 가져옵니다.
    환경 변수에서 키 파일 경로를 읽어와 서비스 계정 인증을 수행합니다.
    """
    try:
        # 환경 변수에서 키 파일 경로 가져오기
        key_path = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY_PATH')
        if not key_path:
            print("[WARNING] GOOGLE_SERVICE_ACCOUNT_KEY_PATH 환경 변수가 설정되지 않았습니다.")
            return None
        
        # 절대 경로로 변환
        if not os.path.isabs(key_path):
            key_path = os.path.join(settings.BASE_DIR, key_path)
        
        # 키 파일 존재 확인
        if not os.path.exists(key_path):
            print(f"[ERROR] 서비스 계정 키 파일을 찾을 수 없습니다: {key_path}")
            return None
        
        # 서비스 계정 크레덴셜 생성
        scopes = [
            'https://www.googleapis.com/auth/drive.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        
        credentials = service_account.Credentials.from_service_account_file(
            key_path, 
            scopes=scopes
        )
        
        print(f"[INFO] 서비스 계정 크레덴셜 생성 성공: {credentials.service_account_email}")
        return credentials
        
    except Exception as e:
        print(f"[ERROR] 서비스 계정 크레덴셜 생성 실패: {str(e)}")
        return None

def get_drive_service_with_service_account():
    """
    서비스 계정을 사용하여 Google Drive 서비스를 생성합니다.
    """
    try:
        credentials = get_service_account_credentials()
        if not credentials:
            return None
        
        service = build('drive', 'v3', credentials=credentials)
        print("[INFO] Google Drive 서비스 생성 성공 (서비스 계정)")
        return service
        
    except Exception as e:
        print(f"[ERROR] Google Drive 서비스 생성 실패: {str(e)}")
        return None

def test_service_account_access():
    """
    서비스 계정 접근을 테스트합니다.
    """
    try:
        service = get_drive_service_with_service_account()
        if not service:
            return False, "서비스 계정 크레덴셜 생성 실패"
        
        # 간단한 API 호출로 테스트
        about = service.about().get(fields="user").execute()
        user_info = about.get('user', {})
        
        print(f"[INFO] 서비스 계정 테스트 성공: {user_info.get('emailAddress', 'Unknown')}")
        return True, "서비스 계정 접근 성공"
        
    except Exception as e:
        error_msg = f"서비스 계정 테스트 실패: {str(e)}"
        print(f"[ERROR] {error_msg}")
        return False, error_msg
