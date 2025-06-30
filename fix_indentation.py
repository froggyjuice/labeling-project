#!/usr/bin/env python3
"""
들여쓰기 문제를 자동으로 수정하는 스크립트
"""

def fix_indentation_issues():
    with open('labeling/views.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 수정할 라인들 (줄 번호는 1-based)
    fixes = [
        (1109, "        if 'drive_credentials' not in request.session:\n"),
        (1110, "            return JsonResponse({'error': 'Google Drive authorization required'}, status=401)\n"),
        (1129, "        try:\n"),
        (1130, "            results = service.files().list(\n"),
        (1135, "            files = results.get('files', [])\n"),
        (1136, "            print(f\"[배치 생성] 발견된 이미지: {len(files)}개\")\n"),
        (1138, "            if not files:\n"),
        (1139, "                return JsonResponse({'error': '폴더에 이미지 파일이 없습니다.'}, status=400)\n"),
        (1141, "        except Exception as e:\n"),
        (1142, "            print(f\"[배치 생성] 파일 목록 가져오기 실패: {str(e)}\")\n"),
        (1143, "            return JsonResponse({'error': f'파일 목록 가져오기 실패: {str(e)}'}, status=400)\n"),
    ]
    
    # 라인 수정
    for line_num, new_content in fixes:
        if line_num <= len(lines):
            lines[line_num - 1] = new_content
            print(f"Fixed line {line_num}")
    
    # 파일 다시 쓰기
    with open('labeling/views.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    print("Indentation fixes completed!")

if __name__ == "__main__":
    fix_indentation_issues() 