from typing import Dict, Any, Optional
import os
from functools import partial

from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END

from .document_state import DocumentState
from .nodes import (
    data_loader_node,
    change_analyzer_node,
    document_decider_node,
    document_generator_node,
    document_saver_node,
)

#LangGraph 워크플로우 메인 클래스
class DocumentWorkflow:
    """
    문서 자동 생성/업데이트 워크플로우
    
    5개 노드로 구성:
        1. data_loader: DB에서 데이터 로드
        2. change_analyzer: LLM으로 변경사항 분석
        3. document_decider: 업데이트 vs 신규 생성 결정
        4. document_generator: 마크다운 문서 생성
        5. document_saver: DB에 저장
    """
    
    def __init__(self, openai_api_key: Optional[str] = None, use_mock: bool = False):
        """
        Args:
            openai_api_key: OpenAI API 키 (없으면 환경변수에서 가져옴)
            use_mock: True면 LLM 대신 Mock 응답 사용 (테스트/개발용)
        """
        self.use_mock = use_mock
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        
        # LLM 초기화
        if not use_mock:
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is required (or use use_mock=True)")
            
            self.llm = ChatOpenAI(
                api_key=self.api_key,
                model="gpt-3.5-turbo",
                temperature=0.1
            )
        else:
            self.llm = None  # Mock 모드에서는 LLM 사용 안함
        
        # 워크플로우 빌드
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """LangGraph 워크플로우 구성"""
        workflow = StateGraph(DocumentState)
        
        # 노드 추가 (각 노드는 독립적인 파일에서 가져옴)
        workflow.add_node("data_loader", data_loader_node)
        
        # partial을 사용하여 llm과 use_mock을 바인딩
        workflow.add_node(
            "change_analyzer",
            partial(change_analyzer_node, llm=self.llm, use_mock=self.use_mock)
        )
        
        workflow.add_node("document_decider", document_decider_node)
        
        workflow.add_node(
            "document_generator",
            partial(document_generator_node, llm=self.llm, use_mock=self.use_mock)
        )
        
        workflow.add_node("document_saver", document_saver_node)
        
        # 워크플로우 연결
        workflow.set_entry_point("data_loader")
        workflow.add_edge("data_loader", "change_analyzer")
        workflow.add_edge("change_analyzer", "document_decider")
        workflow.add_edge("document_decider", "document_generator")
        workflow.add_edge("document_generator", "document_saver")
        workflow.add_edge("document_saver", END)
        
        return workflow.compile()
    
    def process(self, code_change_id: int) -> Dict[str, Any]:
        """
        워크플로우 실행
        
        Args:
            code_change_id: CodeChange ID
            
        Returns:
            {
                "success": True/False,
                "document_id": int,
                "action": "created" | "updated",
                "title": str,
                "summary": str,
                "error": str  # 실패 시
            }
        """
        initial_state: DocumentState = {
            "code_change_id": code_change_id,
            "status": "loading",
            "should_update": False,
        }
        
        result = self.workflow.invoke(initial_state)
        
        if result.get("status") == "completed":
            return {
                "success": True,
                "document_id": result.get("document_id"),
                "action": result.get("action"),
                "title": result.get("document_title"),
                "summary": result.get("document_summary"),
            }
        else:
            return {
                "success": False,
                "error": result.get("error", "Unknown error"),
            }
