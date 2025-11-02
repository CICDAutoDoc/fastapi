from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..document_state import DocumentState

#LLM 또는 Mock을 사용하여 마크다운 문서를 생성/업데이트하는 노드


def document_generator_node(
    state: DocumentState,
    llm: Optional[ChatOpenAI] = None,
    use_mock: bool = False
) -> DocumentState:
    """
    문서 생성/업데이트 노드
    
    역할:
        - 분석 결과를 기반으로 마크다운 문서 생성
        - Mock 모드: 템플릿 기반 문서
        - 실제 모드: LLM 기반 고품질 문서
        - 문서 요약 생성
    
    입력:
        - should_update: 업데이트 여부
        - analysis_result: 변경사항 분석 결과
        - existing_document: 기존 문서 (업데이트 시)
        - code_change: 커밋 정보
        - changed_files: 변경된 파일 목록
        - llm: ChatOpenAI 인스턴스 (실제 모드)
        - use_mock: Mock 모드 사용 여부
    
    출력:
        - document_content: 생성된 마크다운 문서
        - document_summary: 문서 요약
        - status: "saving"
    """
    try:
        should_update = state.get("should_update", False)
        analysis_result = state.get("analysis_result", "")
        
        print(f"[DocumentGenerator] should_update: {should_update}")
        print(f"[DocumentGenerator] analysis_result length: {len(analysis_result) if analysis_result else 0}")
        
        # Mock 모드 처리
        if use_mock:
            commit_info = state.get("code_change", {})
            changed_files = state.get("changed_files", []) or []
            commit_sha = commit_info.get("commit_sha", "unknown")[:8] if commit_info else "unknown"
            commit_message = commit_info.get("commit_message", "") if commit_info else ""
            
            mock_content = f"""# {commit_sha} 코드 변경사항

##  변경사항 요약
{analysis_result}

##  커밋 정보
- SHA: {commit_sha}
- 메시지: {commit_message}
- 변경된 파일: {', '.join(changed_files)}

##  상세 내용
Mock 모드로 생성된 문서입니다. 
실제 OpenAI API를 사용하면 더 상세한 분석이 제공됩니다.
"""
            
            state["document_content"] = mock_content
            state["document_summary"] = f"{commit_sha} 커밋의 코드 변경사항 문서"
            state["status"] = "saving"
            return state
        
        # 실제 LLM 사용
        if llm is None:
            raise ValueError("LLM is required for non-mock mode")
        
        if should_update:
            # 기존 문서 업데이트
            existing_content = state.get("existing_document", {}).get("content", "")
            
            system_prompt = """당신은 기술 문서 편집 전문가입니다.
기존 문서에 새로운 변경사항을 추가하여 업데이트하세요.

**규칙**:
1. 기존 문서 구조를 유지하세요
2. 새로운 변경사항을 적절한 섹션에 추가하세요
3. 중복된 내용은 통합하세요
4. 마크다운 형식을 유지하세요
5. 변경사항만 간결하게 추가하세요"""

            user_prompt = f"""기존 문서:
```markdown
{existing_content}
```

새로운 변경사항:
{analysis_result}

기존 문서에 새로운 변경사항을 추가하여 업데이트된 문서를 작성하세요."""

        else:
            # 신규 문서 생성
            system_prompt = """당신은 기술 문서 작성 전문가입니다.
코드 변경사항 분석 결과를 바탕으로 기술 문서를 작성하세요.

**문서 구조**:
# 제목

## 개요
- 변경 일시
- 커밋 정보
- 변경된 파일 목록

## 주요 변경사항
- 새로 추가된 기능
- 수정된 기능
- 삭제된 기능

## 기술적 세부사항
- 구현 방법
- 사용된 기술/라이브러리
- 코드 구조 변경

## 영향도
- 기존 시스템에 미치는 영향
- 주의사항

마크다운 형식으로 작성하고, 코드 변경사항과 관련된 내용만 포함하세요."""

            commit_info = state.get("code_change", {})
            changed_files = state.get("changed_files", [])
            
            user_prompt = f"""변경사항 분석:
{analysis_result}

커밋 정보:
- SHA: {commit_info.get('commit_sha', '')}
- 메시지: {commit_info.get('commit_message', '')}
- 작성자: {commit_info.get('author', '')}
- 시간: {commit_info.get('timestamp', '')}

변경된 파일: {', '.join(changed_files)}

위 정보를 바탕으로 기술 문서를 작성하세요."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        
        state["document_content"] = response.content
        
        # 요약 생성
        summary_prompt = f"""다음 문서를 3-5줄로 요약하세요:

{response.content}

요약:"""
        
        summary_response = llm.invoke([HumanMessage(content=summary_prompt)])
        state["document_summary"] = summary_response.content
        
        state["status"] = "saving"
        return state
        
    except Exception as e:
        state["error"] = f"Document generator failed: {str(e)}"
        state["status"] = "error"
        return state
