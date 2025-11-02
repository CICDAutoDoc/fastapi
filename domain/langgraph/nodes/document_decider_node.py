"""
③ 문서 결정 노드

기존 문서 업데이트 또는 신규 생성을 결정하는 노드
"""
from ..document_state import DocumentState


def document_decider_node(state: DocumentState) -> DocumentState:
    """
    문서 결정 노드
    
    역할:
        - 기존 문서 존재 여부 확인
        - 업데이트 또는 신규 생성 결정
        - 문서 제목 설정
    
    입력:
        - existing_document: 기존 문서 정보 (있으면)
        - repository_name: 저장소 이름
        - code_change: 커밋 정보
    
    출력:
        - should_update: True (업데이트) / False (신규 생성)
        - document_title: 문서 제목
    
    로직:
        - existing_document가 있으면:
            * should_update = True
            * 기존 제목 유지
        - existing_document가 없으면:
            * should_update = False
            * 새 제목 생성: "{repo_name} 코드 변경사항 ({commit_sha})"
    """
    try:
        existing_doc = state.get("existing_document")
        
        if existing_doc:
            # 기존 문서 업데이트
            state["should_update"] = True
            state["document_title"] = existing_doc["title"]  # 기존 제목 유지
        else:
            # 신규 문서 생성
            state["should_update"] = False
            
            # 신규 문서 제목 생성
            repo_name = state.get("repository_name", "unknown")
            code_change = state.get("code_change", {})
            commit_sha = code_change.get("commit_sha", "")[:8] if code_change else "unknown"
            
            state["document_title"] = f"{repo_name} 코드 변경사항 ({commit_sha})"
        
        return state
        
    except Exception as e:
        state["error"] = f"Document decider failed: {str(e)}"
        state["status"] = "error"
        return state
