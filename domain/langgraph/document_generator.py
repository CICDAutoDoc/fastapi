import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from typing_extensions import TypedDict
from pydantic import BaseModel
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String


@dataclass
class CodeChangeInput:
    """코드 변경 입력 데이터"""
    commit_sha: str
    commit_message: str
    author_name: str
    repository_name: str
    timestamp: str
    files: List[Dict[str, Any]]
    total_changes: int


class DocumentState(TypedDict):
    """문서 생성 상태"""
    code_input: CodeChangeInput
    analysis_result: str
    document_content: str
    summary: str
    metadata: Dict[str, Any]
    messages: List[Any]


class DocumentGenerator:
    """LLM 기반 문서 생성기"""

    def __init__(self, openai_api_key: Optional[str] = None):
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            api_key=openai_api_key
        )
        self.parser = StrOutputParser()
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Langgraph 워크플로우 구성"""

        # 상태 그래프 생성
        workflow = StateGraph(DocumentState)

        # 노드 추가
        workflow.add_node("analyze_changes", self._analyze_changes)
        workflow.add_node("generate_document", self._generate_document)
        workflow.add_node("create_summary", self._create_summary)

        # 엣지 추가
        workflow.set_entry_point("analyze_changes")
        workflow.add_edge("analyze_changes", "generate_document")
        workflow.add_edge("generate_document", "create_summary")
        workflow.add_edge("create_summary", END)

        return workflow.compile()

    async def _analyze_changes(self, state: DocumentState) -> DocumentState:
        """코드 변경사항 분석"""
        code_input = state["code_input"]

        # 변경 파일들 정리
        file_summaries = []
        for file_info in code_input.files:
            file_summary = f"""
파일: {file_info['filename']}
상태: {file_info['status']}
변경 라인: {file_info['changes']} (+{file_info['additions']}, -{file_info['deletions']})
"""
            if file_info.get('patch'):
                file_summary += f"변경사항:\n```diff\n{file_info['patch'][:1000]}\n```"

            file_summaries.append(file_summary)

        # 분석 프롬프트
        analysis_prompt = f"""
다음 코드 변경사항을 분석해주세요:

**커밋 정보:**
- SHA: {code_input.commit_sha}
- 메시지: {code_input.commit_message}
- 작성자: {code_input.author_name}
- 저장소: {code_input.repository_name}
- 시간: {code_input.timestamp}
- 총 변경 라인: {code_input.total_changes}

**변경된 파일들:**
{''.join(file_summaries)}

이 변경사항을 분석하여 다음을 제공해주세요:
1. 주요 변경사항 요약
2. 변경의 목적과 의도
3. 영향을 받는 기능들
4. 기술적 세부사항
"""

        messages = [
            SystemMessage(content="당신은 코드 변경사항을 분석하는 전문가입니다. 변경사항을 정확하고 구체적으로 분석해주세요."),
            HumanMessage(content=analysis_prompt)
        ]

        try:
            analysis_result = await self.llm.ainvoke(messages)
            state["analysis_result"] = analysis_result.content
            state["messages"] = add_messages(state.get("messages", []), messages)
        except Exception as e:
            state["analysis_result"] = f"분석 실패: {str(e)}"

        return state

    async def _generate_document(self, state: DocumentState) -> DocumentState:
        """문서 생성"""
        code_input = state["code_input"]
        analysis = state["analysis_result"]

        document_prompt = f"""
다음 코드 변경사항에 대한 기술 문서를 작성해주세요:

**분석 결과:**
{analysis}

**커밋 정보:**
- 커밋: {code_input.commit_sha}
- 메시지: {code_input.commit_message}
- 작성자: {code_input.author_name}
- 저장소: {code_input.repository_name}

다음 형식으로 마크다운 문서를 작성해주세요:

# 제목

## 변경사항 개요
- 간단한 변경 요약

## 주요 변경 내용
- 구체적인 변경사항들

## 기술적 세부사항
- 코드 레벨의 변경사항
- 아키텍처 영향

## 영향 범위
- 어떤 기능이 영향을 받는지

## 주의사항
- 개발자들이 알아야 할 중요한 점들

문서는 한국어로 작성하고, 개발팀이 쉽게 이해할 수 있도록 명확하고 구체적으로 작성해주세요.
"""

        messages = [
            SystemMessage(content="당신은 기술 문서 작성 전문가입니다. 개발팀을 위한 명확하고 유용한 문서를 작성해주세요."),
            HumanMessage(content=document_prompt)
        ]

        try:
            document_result = await self.llm.ainvoke(messages)
            state["document_content"] = document_result.content
            state["messages"] = add_messages(state.get("messages", []), messages)
        except Exception as e:
            state["document_content"] = f"# 문서 생성 실패\n\n{str(e)}"

        return state

    async def _create_summary(self, state: DocumentState) -> DocumentState:
        """문서 요약 생성"""
        document_content = state["document_content"]

        summary_prompt = f"""
다음 문서의 핵심 내용을 3-4문장으로 요약해주세요:

{document_content}

요약은 한국어로 작성하고, 가장 중요한 변경사항과 영향을 중심으로 해주세요.
"""

        messages = [
            SystemMessage(content="문서의 핵심 내용을 간결하게 요약해주세요."),
            HumanMessage(content=summary_prompt)
        ]

        try:
            summary_result = await self.llm.ainvoke(messages)
            state["summary"] = summary_result.content

            # 메타데이터 생성
            state["metadata"] = {
                "generation_time": datetime.utcnow().isoformat(),
                "model": "gpt-4o-mini",
                "langgraph_version": "0.1.0",
                "analysis_length": len(state.get("analysis_result", "")),
                "document_length": len(document_content),
                "file_count": len(state["code_input"].files)
            }
        except Exception as e:
            state["summary"] = f"요약 생성 실패: {str(e)}"
            state["metadata"] = {"error": str(e)}

        return state

    async def generate_document(self, code_input: CodeChangeInput) -> Dict[str, Any]:
        """
        메인 문서 생성 함수

        Args:
            code_input: 코드 변경 입력 데이터

        Returns:
            생성된 문서와 메타데이터
        """
        try:
            # 초기 상태 설정
            initial_state = DocumentState(
                code_input=code_input,
                analysis_result="",
                document_content="",
                summary="",
                metadata={},
                messages=[]
            )

            # 워크플로우 실행
            result = await self.workflow.ainvoke(initial_state)

            return {
                "success": True,
                "title": self._extract_title(result["document_content"]),
                "content": result["document_content"],
                "summary": result["summary"],
                "metadata": result["metadata"]
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "title": f"문서 생성 실패: {code_input.commit_message[:50]}",
                "content": f"# 오류 발생\n\n문서 생성 중 오류가 발생했습니다: {str(e)}",
                "summary": f"문서 생성 실패: {str(e)}",
                "metadata": {"error": str(e), "failed_at": datetime.utcnow().isoformat()}
            }

    def _extract_title(self, content: str) -> str:
        """마크다운에서 제목 추출"""
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return "자동 생성 문서"


# 전역 생성기 인스턴스
_generator_instance: Optional[DocumentGenerator] = None


def get_document_generator(openai_api_key: Optional[str] = None) -> DocumentGenerator:
    """문서 생성기 싱글톤 인스턴스 반환"""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = DocumentGenerator(openai_api_key)
    return _generator_instance


# Mock 생성기 (테스트/개발용)
class MockDocumentGenerator:
    """개발/테스트용 Mock 문서 생성기"""

    async def generate_document(self, code_input: CodeChangeInput) -> Dict[str, Any]:
        """Mock 문서 생성"""
        await asyncio.sleep(1)  # 처리 시간 시뮬레이션

        title = f"코드 변경 문서: {code_input.commit_message[:50]}"

        content = f"""# {title}

## 변경사항 개요
- **커밋**: `{code_input.commit_sha}`
- **메시지**: {code_input.commit_message}
- **작성자**: {code_input.author_name}
- **저장소**: {code_input.repository_name}
- **시간**: {code_input.timestamp}
- **총 변경 라인**: {code_input.total_changes}

## 주요 변경 내용

이번 커밋에서는 다음과 같은 파일들이 변경되었습니다:

"""

        for file_info in code_input.files:
            content += f"""
### {file_info['filename']}
- **상태**: {file_info['status']}
- **변경 라인**: {file_info['changes']} (+{file_info['additions']}, -{file_info['deletions']})

"""
            if file_info.get('patch'):
                content += f"""**변경사항:**
```diff
{file_info['patch'][:500]}
```

"""

        content += f"""
## 기술적 세부사항
- 총 {len(code_input.files)}개의 파일이 변경되었습니다.
- 전체 {code_input.total_changes}라인의 코드가 수정되었습니다.

## 영향 범위
변경된 파일들을 기반으로 다음 영역에 영향을 줄 수 있습니다:
{', '.join([f['filename'].split('/')[-1] for f in code_input.files])}

## 주의사항
- 변경사항을 적용하기 전에 관련 테스트를 실행해주세요.
- 의존성이 있는 다른 모듈들도 확인해주세요.

---
*이 문서는 Mock 생성기에 의해 자동 생성되었습니다. ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})*
"""

        return {
            "success": True,
            "title": title,
            "content": content,
            "summary": f"{code_input.commit_message} - {len(code_input.files)}개 파일, {code_input.total_changes}라인 변경",
            "metadata": {
                "generation_time": datetime.utcnow().isoformat(),
                "model": "mock",
                "file_count": len(code_input.files),
                "total_changes": code_input.total_changes,
                "processing_time": 1.0
            }
        }