import os
import json
from django.conf import settings

def get_google_oauth_config():
    """
    환경 변수에서 Google OAuth 설정을 가져옵니다.
    프로덕션에서는 환경 변수, 개발에서는 파일 백업 시도
    """
    # 환경 변수에서 직접 가져오기 (프로덕션 환경)
    client_id = os.environ.get('GOOGLE_CLIENT_ID') or os.environ.get('GOOGLE_OAUTH_CLIENT_ID')
    client_secret = os.environ.get('GOOGLE_CLIENT_SECRET') or os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET')
    
    if client_id and client_secret:
        return {
            'client_id': client_id,
            'client_secret': client_secret,
            'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
            'token_uri': 'https://oauth2.googleapis.com/token',
            'redirect_uris': ['http://127.0.0.1:8000/google-auth-callback/']
        }
    
    # 개발 환경에서 파일이 있는 경우만 사용 (백업)
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'client_id.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config['web']
    
    # 환경 변수가 설정되지 않은 경우 기본값 반환 (개발 환경)
    print("[WARNING] Google OAuth 환경 변수가 설정되지 않았습니다. 일부 기능이 제한될 수 있습니다.")
    return {
        'client_id': 'dummy_client_id',
        'client_secret': 'dummy_client_secret',
        'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
        'token_uri': 'https://oauth2.googleapis.com/token',
        'redirect_uris': ['http://127.0.0.1:8000/google-auth-callback/']
    }
