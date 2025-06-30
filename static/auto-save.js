// 자동 저장 기능 개선
document.addEventListener('DOMContentLoaded', function() {
    console.log('자동 저장 기능 활성화');
    
    // 기존 selectLabel 함수를 자동 저장 버전으로 교체
    const originalSelectLabel = window.selectLabel;
    
    window.selectLabel = async function(label) {
        console.log('자동 저장 selectLabel 호출:', label);
        
        // 기존 라벨 선택 로직
        const btn = document.querySelector(`[data-label="${label}"]`);
        if (!btn) return;
        
        if (btn.classList.contains('selected')) {
            btn.classList.remove('selected');
            if (window.labelingState) {
                window.labelingState.selectedLabels = window.labelingState.selectedLabels.filter(l => l !== label);
            }
        } else {
            btn.classList.add('selected');
            if (window.labelingState) {
                window.labelingState.selectedLabels.push(label);
            }
        }
        
        // 자동 저장 실행
        if (window.labelingState && window.labelingState.selectedLabels.length > 0) {
            const currentImageId = window.labelingState.getCurrentImageId();
            if (currentImageId) {
                try {
                    const success = await window.labelingState.saveLabelToServer(currentImageId, window.labelingState.selectedLabels);
                    if (success) {
                        window.labelingState.hasChanges = false;
                        console.log('✅ 자동 저장 완료');
                        
                        // 저장 상태 표시 (선택사항)
                        showAutoSaveStatus('저장됨');
                    }
                } catch (error) {
                    console.error('자동 저장 실패:', error);
                }
            }
        }
    };
    
    // 저장 상태 표시 함수
    function showAutoSaveStatus(message) {
        // 기존 상태 메시지 제거
        const existing = document.getElementById('autoSaveStatus');
        if (existing) existing.remove();
        
        // 새 상태 메시지 생성
        const status = document.createElement('div');
        status.id = 'autoSaveStatus';
        status.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #28a745;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 14px;
            z-index: 1000;
            opacity: 0;
            transition: opacity 0.3s ease;
        `;
        status.textContent = message;
        document.body.appendChild(status);
        
        // 애니메이션
        setTimeout(() => status.style.opacity = '1', 100);
        setTimeout(() => {
            status.style.opacity = '0';
            setTimeout(() => status.remove(), 300);
        }, 2000);
    }
    
    // 저장 버튼 숨기기 또는 텍스트 변경
    const saveButton = document.querySelector('button[onclick*="saveProgress"], button[onclick*="saveCurrentProgress"]');
    if (saveButton) {
        saveButton.style.display = 'none'; // 저장 버튼 숨기기
        // 또는 텍스트만 변경하려면:
        // saveButton.textContent = '진행상황 저장 (자동저장 활성화됨)';
        // saveButton.style.opacity = '0.5';
    }
    
    // Home/Dashboard 버튼에만 경고 추가
    const homeButtons = document.querySelectorAll('.home-btn, .breadcrumb-item');
    homeButtons.forEach(button => {
        const originalClick = button.onclick;
        button.onclick = function(e) {
            if (window.labelingState && window.labelingState.hasChanges) {
                e.preventDefault();
                showSaveConfirmation(() => {
                    if (originalClick) {
                        originalClick.call(this, e);
                    } else {
                        window.location.href = '/dashboard/';
                    }
                });
            } else {
                if (originalClick) {
                    originalClick.call(this, e);
                } else {
                    window.location.href = '/dashboard/';
                }
            }
        };
    });
    
    console.log('자동 저장 기능 설정 완료');
});

// 저장 확인 모달 (간단 버전)
function showSaveConfirmation(callback) {
    const confirmResult = confirm('현재까지의 진행상황을 저장하고 나가시겠습니까?\n\n확인: 저장 후 나가기\n취소: 저장없이 나가기');
    
    if (confirmResult && window.labelingState && window.labelingState.saveProgress) {
        // 저장 후 나가기
        window.labelingState.saveProgress().then(() => {
            callback();
        });
    } else {
        // 저장없이 나가기
        callback();
    }
} 