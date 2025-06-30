# 기본 썸네일 이미지

## 필요한 기본 이미지 파일들

1. **default-batch-thumbnail.png** (200x150px)
   - 배치에 이미지가 없을 때 표시되는 기본 썸네일
   - 회색 배경에 "이미지 없음" 텍스트 또는 폴더 아이콘

2. **image-error.png** (200x150px)
   - 이미지 로드 실패 시 표시되는 오류 이미지
   - 빨간색 배경에 "이미지 오류" 텍스트

## 임시 대체 방안

기본 이미지가 없는 경우, 다음 CSS를 사용하여 텍스트로 대체:

```css
.thumbnail-placeholder {
    width: 200px;
    height: 150px;
    background: #f8f9fa;
    border: 2px dashed #dee2e6;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.9rem;
    color: #6c757d;
    text-align: center;
}
```

## 배치 시 자동 생성

`thumbnail_utils.py`의 함수들이 다음과 같이 작동합니다:
- 이미지 있음: Google Drive 프록시 URL 또는 직접 URL
- 이미지 없음: `/static/images/default-batch-thumbnail.png`
- 오류 발생: `/static/images/image-error.png` 