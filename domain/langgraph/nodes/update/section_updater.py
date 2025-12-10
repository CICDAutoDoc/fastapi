"""
섹션 업데이터 모듈

개별 섹션을 업데이트하는 핵심 로직을 제공합니다.
"""

from typing import List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from ...utils.llm_backoff import invoke_with_retry
from .prompt_builder import build_section_prompt
from .content_merger import merge_changelog, merge_section_changes


def update_section_llm(
    section_key: str,
    old_text: str,
    llm: ChatOpenAI,
    file_summaries: List[dict],
    analysis: str,
    commit_msg: str
) -> str:
    """LLM으로 특정 섹션 업데이트 (변경 부분만 생성 후 병합)"""
    system, user = build_section_prompt(section_key, old_text, file_summaries, analysis, commit_msg)
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    resp = invoke_with_retry(llm, messages)
    content = getattr(resp, 'content', '')
    if isinstance(content, list):
        content = '\n'.join(str(c) for c in content)
    
    generated = str(content).strip()
    
    # Changelog는 기존 내용에 추가만
    if section_key == 'changelog':
        return merge_changelog(old_text, generated)
    
    # 나머지 모든 섹션은 완전 재생성 (마커 없이 전체 교체)
    # overview, architecture, diagram, modules
    return generated


def update_section_mock(section_key: str, old_text: str, commit_msg: str) -> str:
    """Mock 모드로 섹션 업데이트 (병합 방식)"""
    if section_key == 'changelog':
        # Changelog는 항상 추가
        new_entry = f"- {commit_msg[:60]}"
        return merge_changelog(old_text, new_entry)
    
    # 일반 섹션: 간단한 추가 주석
    mock_addition = f"\n\n*Updated: {commit_msg[:50]}*"
    return old_text.rstrip() + mock_addition


def infer_target_sections(changed_files: List[str]) -> List[str]:
    """변경된 파일 기반으로 업데이트할 섹션 추론"""
    targets = set()
    for f in changed_files:
        lf = f.lower()
        if any(x in lf for x in ['main', 'app', 'config']):
            targets.add('overview')
        if any(x in lf for x in ['router', 'endpoint', 'controller']):
            targets.add('architecture')
            targets.add('diagram')  # 아키텍처 변경 시 다이어그램도 업데이트
            targets.add('modules')
        if any(x in lf for x in ['model', 'schema', 'entity']):
            targets.add('modules')
        if any(x in lf for x in ['service', 'handler']):
            targets.add('modules')
        if any(x in lf for x in ['test', 'spec']):
            targets.add('changelog')
    targets.add('changelog')  # 항상 changelog 포함
    return list(targets)
