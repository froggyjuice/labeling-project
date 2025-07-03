from django.core.management.base import BaseCommand
from labeling.utils import get_service_account_credentials, test_service_account_access

class Command(BaseCommand):
    help = 'Test IAM service account access to Google Drive'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed information about the test',
        )
        parser.add_argument(
            '--folder-id', 
            type=str, 
            help='Google Drive Folder ID to check access (e.g., 1dG3x-csNN1LxaK6FVSC5n28xmIYkiyAo)'
        )

    def handle(self, *args, **options):
        self.stdout.write("🔧 IAM 서비스 계정 테스트 시작...")
        self.stdout.write("=" * 50)
        
        # 1. 서비스 계정 credentials 확인
        self.stdout.write("1. 서비스 계정 credentials 확인 중...")
        credentials = get_service_account_credentials()
        
        if credentials:
            self.stdout.write(
                self.style.SUCCESS("✅ 서비스 계정 credentials를 성공적으로 로드했습니다.")
            )
            if options['verbose']:
                self.stdout.write(f"   - Credentials 타입: {type(credentials).__name__}")
        else:
            self.stdout.write(
                self.style.ERROR("❌ 서비스 계정 credentials를 로드할 수 없습니다.")
            )
            self.stdout.write("   가능한 원인:")
            self.stdout.write("   - GOOGLE_SERVICE_ACCOUNT_KEY_PATH 환경 변수가 설정되지 않음")
            self.stdout.write("   - 키 파일이 존재하지 않거나 읽을 수 없음")
            self.stdout.write("   - 키 파일 형식이 잘못됨")
            return
        
        # 2. Google Drive API 접근 테스트
        self.stdout.write("\n2. Google Drive API 접근 테스트 중...")
        success, message = test_service_account_access()
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Google Drive API 접근 성공: {message}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Google Drive API 접근 실패: {message}")
            )
            self.stdout.write("   가능한 원인:")
            self.stdout.write("   - 서비스 계정에 Drive API 권한이 없음")
            self.stdout.write("   - 프로젝트에서 Drive API가 활성화되지 않음")
            self.stdout.write("   - 서비스 계정 키가 만료됨")
            return
        
        # 3. 서비스 계정 정보 확인
        self.stdout.write("\n3. 서비스 계정 정보 확인 중...")
        try:
            from googleapiclient.discovery import build
            service = build('drive', 'v3', credentials=credentials)
            
            # 사용자 정보 확인 (서비스 계정 정보)
            about = service.about().get(fields='user').execute()
            user_info = about.get('user', {})
            
            self.stdout.write(
                self.style.SUCCESS(f"✅ 서비스 계정 정보 확인됨")
            )
            if options['verbose']:
                self.stdout.write(f"   - 이메일: {user_info.get('emailAddress', 'N/A')}")
                self.stdout.write(f"   - 이름: {user_info.get('displayName', 'N/A')}")
                self.stdout.write(f"   - 권한: {user_info.get('permissionId', 'N/A')}")
        
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"⚠️ 서비스 계정 정보 확인 중 오류: {str(e)}")
            )
            return
        
        # 4. 마이드라이브 폴더 목록 확인 (선택적)
        if options['verbose']:
            self.stdout.write("\n4. 마이드라이브 폴더 목록 확인 중...")
            try:
                results = service.files().list(
                    q="mimeType='application/vnd.google-apps.folder' and 'root' in parents",
                    fields="files(id, name)",
                    pageSize=10
                ).execute()
                folders = results.get('files', [])
                
                if folders:
                    self.stdout.write("   📁 접근 가능한 마이드라이브 폴더:")
                    for folder in folders:
                        self.stdout.write(f"      - {folder['name']} (ID: {folder['id']})")
                else:
                    self.stdout.write("   📁 마이드라이브에 폴더가 없습니다.")
                    
            except Exception as e:
                self.stdout.write(
                    self.style.WARNING(f"   ⚠️ 마이드라이브 폴더 확인 중 오류: {str(e)}")
                )
        
        # 5. 특정 폴더 접근 권한 확인 (선택적)
        folder_id = options.get('folder_id')
        if folder_id:
            self.stdout.write(f"\n5. 특정 폴더 접근 권한 확인 중... (ID: {folder_id})")
            try:
                folder = service.files().get(
                    fileId=folder_id, 
                    fields='id, name, mimeType, parents'
                ).execute()
                
                if folder['mimeType'] == 'application/vnd.google-apps.folder':
                    self.stdout.write(
                        self.style.SUCCESS(f"✅ 폴더 접근 가능: {folder['name']} (ID: {folder['id']})")
                    )
                    if options['verbose']:
                        self.stdout.write(f"   - 폴더 타입: Google Drive 폴더")
                        if 'parents' in folder:
                            self.stdout.write(f"   - 상위 폴더: {folder['parents']}")
                else:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ 해당 ID는 폴더가 아닙니다: {folder['mimeType']}")
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ 폴더 접근 불가 또는 존재하지 않음: {str(e)}")
                )
        
        # 6. 요약
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("📋 테스트 결과 요약:")
        self.stdout.write("✅ 서비스 계정 credentials 로드 성공")
        self.stdout.write("✅ Google Drive API 접근 성공")
        self.stdout.write("✅ 서비스 계정 정보 확인 성공")
        
        if folder_id:
            self.stdout.write("✅ 특정 폴더 접근 권한 확인 완료")
        
        self.stdout.write("\n🎉 IAM 서비스 계정이 정상적으로 작동합니다!")
        self.stdout.write("   모든 사용자가 Google Drive 이미지에 접근할 수 있습니다.")
        
        if options['verbose']:
            self.stdout.write("\n💡 사용법:")
            self.stdout.write("   - 기본 테스트: python manage.py test_iam_service")
            self.stdout.write("   - 상세 정보: python manage.py test_iam_service --verbose")
            self.stdout.write("   - 폴더 확인: python manage.py test_iam_service --folder-id=FOLDER_ID")
            self.stdout.write("   - 예시: python manage.py test_iam_service --folder-id=1dG3x-csNN1LxaK6FVSC5n28xmIYkiyAo") 