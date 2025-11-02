"""
LangGraph 워크플로우 상태 정의

문서 자동 생성/업데이트 워크플로우의 상태를 관리합니다.
"""
from typing import TypedDict, List, Optional, Dict, Any
from dataclasses import dataclass


class DocumentState(TypedDict, total=False):
    """
    LangGraph 워크플로우 상태
    
    워크플로우 단계:
    1. DataLoader: code_change_id로 DB에서 데이터 로드
    2. ChangeAnalyzer: diff를 LLM으로 분석
    3. DocumentDecider: 기존 문서 업데이트 vs 신규 생성 결정
    4. DocumentGenerator: 문서 생성 또는 업데이트
    5. DocumentSaver: DB에 저장 (draft 상태)
    """
    
    # ========== 입력 데이터 ==========
    code_change_id: int  # CodeChange ID (필수 입력)
    
    # ========== 로드된 데이터 ==========
    code_change: Optional[Dict[str, Any]]  # CodeChange 정보 (commit_sha, message, timestamp 등)
    file_changes: Optional[List[Dict[str, Any]]]  # FileChange 목록 (filename, status, patch 등)
    diff_content: Optional[str]  # 통합된 diff 내용
    changed_files: Optional[List[str]]  # 변경된 파일명 목록
    repository_name: Optional[str]  # 저장소 full_name
    
    existing_document: Optional[Dict[str, Any]]  # 기존 문서 (있는 경우)
    
    # ========== 분석 결과 ==========
    analysis_result: Optional[str]  # LLM 분석 결과 (변경사항 요약)
    
    # ========== 문서 생성 결과 ==========
    should_update: bool  # True: 기존 문서 업데이트, False: 신규 생성
    document_title: Optional[str]  # 문서 제목
    document_content: Optional[str]  # 생성/업데이트된 문서 본문 (마크다운)
    document_summary: Optional[str]  # 문서 요약
    
    # ========== 저장 결과 ==========
    document_id: Optional[int]  # 저장된 Document ID
    action: Optional[str]  # "created" 또는 "updated"
    
    # ========== 상태 및 에러 ==========
    status: str  # "loading", "analyzing", "generating", "saving", "completed", "error"
    error: Optional[str]  # 에러 메시지