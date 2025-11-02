"""
② 변경사항 분석 노드

LLM 또는 Mock을 사용하여 코드 변경사항을 분석하는 노드
"""
from typing import Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

from ..document_state import DocumentState


def change_analyzer_node(
    state: DocumentState,
    llm: Optional[ChatOpenAI] = None,
    use_mock: bool = False
) -> DocumentState:
    """
    변경사항 분석 노드
    
    역할:
        - Git diff를 분석하여 변경사항 요약 생성
        - Mock 모드: 템플릿 기반 분석
        - 실제 모드: LLM 기반 상세 분석
    
    입력:
        - diff_content: Git diff 내용
        - changed_files: 변경된 파일 목록
        - code_change: 커밋 정보
        - llm: ChatOpenAI 인스턴스 (실제 모드)
        - use_mock: Mock 모드 사용 여부
    
    출력:
        - analysis_result: 변경사항 분석 결과
        - status: "generating"
    """
    try:
        diff_content = state.get("diff_content", "")
        changed_files = state.get("changed_files", []) or []
        code_change = state.get("code_change") or {}
        commit_message = code_change.get("commit_message", "") if isinstance(code_change, dict) else ""
        
        if use_mock:
            # Mock 응답 생성
            analysis = f"""## 주요 변경사항
- 파일 수정: {', '.join(changed_files)}
- 커밋 메시지: {commit_message}

## 변경 이유
코드 개선 및 기능 추가를 위한 변경

## 영향 범위
수정된 파일들의 관련 기능에 영향

## 기술적 세부사항
- 수정된 코드 라인 수: {diff_content.count('+') if diff_content else 0}개
- Python 코드 변경"""
            
            state["analysis_result"] = analysis
            state["status"] = "generating"
            return state
        
        # 실제 LLM 분석
        if llm is None:
            raise ValueError("LLM is required for non-mock mode")
        
        system_prompt = """당신은 코드 변경사항을 분석하는 전문가입니다.
주어진 Git diff를 분석하여 다음을 파악해주세요:

1. **주요 변경사항**: 무엇이 추가/수정/삭제되었는가
2. **변경 이유**: 왜 이런 변경이 이루어졌는가 (커밋 메시지 참고)
3. **영향 범위**: 어떤 기능/모듈에 영향을 주는가
4. **기술적 세부사항**: 사용된 기술/패턴/라이브러리

**중요**: 코드 변경사항과 직접 관련된 내용만 작성하세요. 불필요한 내용은 제외합니다."""

        user_prompt = f"""커밋 메시지: {commit_message}

변경된 파일들:
{', '.join(changed_files)}

Git Diff:
{diff_content}

위 코드 변경사항을 분석하여 요약해주세요."""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        response = llm.invoke(messages)
        
        state["analysis_result"] = str(response.content) if hasattr(response, 'content') else str(response)
        state["status"] = "generating"
        return state
        
    except Exception as e:
        state["error"] = f"Change analyzer failed: {str(e)}"
        state["status"] = "error"
        return state
