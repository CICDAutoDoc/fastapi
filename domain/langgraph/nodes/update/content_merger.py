"""
콘텐츠 병합 모듈

변경사항을 기존 콘텐츠와 병합하는 로직을 제공합니다.
"""

import re
from typing import List, Tuple


# ============================================================
# Changelog 병합
# ============================================================

def merge_changelog(old_content: str, new_entry: str) -> str:
    """Changelog 섹션에 새 항목 추가"""
    if not new_entry or '[NO_CHANGE]' in new_entry:
        return old_content
    
    # 기존 내용이 없으면 새 항목만 반환
    if not old_content.strip():
        return new_entry
    
    # 기존 내용 + 새 항목
    return f"{old_content.rstrip()}\n{new_entry}"


# ============================================================
# DELETE 처리 헬퍼 함수들
# ============================================================

def _delete_markdown_header_block(lines: List[str], snippet_key: str, snippet: str) -> List[str]:
    """
    Markdown 헤더(###, ##)를 포함하는 블록을 삭제
    
    Args:
        lines: 원본 텍스트를 줄 단위로 분할한 리스트
        snippet_key: 찾을 텍스트의 키 (앞 30자)
        snippet: 찾을 전체 텍스트
    
    Returns:
        삭제 처리된 줄 리스트
    """
    new_lines = []
    skip_mode = False
    skip_header_level = 0
    
    for line in lines:
        # snippet을 포함하고 헤더인 경우
        if (snippet_key in line or snippet in line) and line.strip().startswith('#'):
            # 헤더 레벨 파악 (# 개수)
            skip_header_level = len(line) - len(line.lstrip('#'))
            skip_mode = True
            continue  # 이 헤더 줄은 건너뛰기
        
        # skip_mode인 경우: 다음 동급/상위 헤더를 만날 때까지 건너뛰기
        if skip_mode:
            if line.strip().startswith('#'):
                # 현재 줄의 헤더 레벨
                current_header_level = len(line) - len(line.lstrip('#'))
                # 동급이거나 상위 헤더면 skip_mode 종료
                if current_header_level <= skip_header_level:
                    skip_mode = False
                    new_lines.append(line)
                # 하위 헤더면 계속 건너뛰기
                continue
            else:
                # 헤더가 아닌 내용은 계속 건너뛰기
                continue
        
        # 일반 줄: snippet을 포함하면 삭제
        if snippet_key in line or snippet in line:
            continue
        
        new_lines.append(line)
    
    return new_lines


def _delete_line_or_paragraph(content: str, snippet_key: str, snippet: str) -> str:
    """
    일반 라인이나 문단 삭제
    
    Args:
        content: 삭제할 대상 텍스트
        snippet_key: 찾을 텍스트의 키 (앞 30자)
        snippet: 찾을 전체 텍스트
    
    Returns:
        삭제 처리된 텍스트
    """
    # 문단 단위로 삭제 시도
    paragraphs = content.split('\n\n')
    new_paragraphs = []
    
    for para in paragraphs:
        # snippet을 포함하는 문단이면 삭제
        if snippet_key in para or snippet in para:
            continue
        new_paragraphs.append(para)
    
    return '\n\n'.join(new_paragraphs)


def _process_delete_markers(content: str, changes: str) -> str:
    """
    [DELETE: ...] 마커를 찾아서 해당 내용 삭제
    
    Args:
        content: 원본 텍스트
        changes: 변경사항 (마커 포함)
    
    Returns:
        삭제 처리된 텍스트
    """
    delete_pattern = re.compile(r'\[DELETE:\s*([^\]]+)\]', re.DOTALL)
    delete_matches = delete_pattern.findall(changes)
    
    result = content
    
    for snippet_to_delete in delete_matches:
        snippet = snippet_to_delete.strip()
        if not snippet:
            continue
        
        snippet_key = snippet[:30] if len(snippet) > 30 else snippet
        
        # 1) Markdown 헤더 블록 삭제 시도
        lines = result.split('\n')
        new_lines = _delete_markdown_header_block(lines, snippet_key, snippet)
        result = '\n'.join(new_lines)
        
        # 2) 헤더가 아닌 경우: 문단 단위 삭제 시도
        if '[DELETE:' in changes:
            result = _delete_line_or_paragraph(result, snippet_key, snippet)
    
    return result


# ============================================================
# UPDATE 처리 헬퍼 함수들
# ============================================================

def _find_and_replace_line(lines: List[str], snippet_key: str, snippet: str, new_text: str) -> Tuple[List[str], bool]:
    """
    줄 단위로 텍스트를 찾아서 교체
    
    Returns:
        (수정된 줄 리스트, 찾았는지 여부)
    """
    for i, line in enumerate(lines):
        if snippet_key in line or snippet in line:
            lines[i] = new_text
            return lines, True
    return lines, False


def _find_and_replace_paragraph(paragraphs: List[str], snippet_key: str, snippet: str, new_text: str) -> Tuple[List[str], bool]:
    """
    문단 단위로 텍스트를 찾아서 교체
    
    Returns:
        (수정된 문단 리스트, 찾았는지 여부)
    """
    for i, para in enumerate(paragraphs):
        if snippet_key in para or snippet in para:
            paragraphs[i] = new_text
            return paragraphs, True
    return paragraphs, False


def _process_update_markers(content: str, changes: str) -> str:
    """
    [UPDATE: ...] 마커를 찾아서 해당 내용 교체
    
    Args:
        content: 원본 텍스트
        changes: 변경사항 (마커 포함)
    
    Returns:
        교체 처리된 텍스트
    """
    update_pattern = re.compile(r'\[UPDATE:\s*([^\]]+)\]\s*\n*([^\[]*?)(?=\[|$)', re.DOTALL)
    matches = update_pattern.findall(changes)
    
    result = content
    
    for original_snippet, new_content in matches:
        snippet = original_snippet.strip()
        new_text = new_content.strip()
        
        if not new_text:
            continue
        
        snippet_key = snippet[:30] if len(snippet) > 30 else snippet
        
        # 1) 줄 단위로 찾기
        lines = result.split('\n')
        lines, found = _find_and_replace_line(lines, snippet_key, snippet, new_text)
        
        if found:
            result = '\n'.join(lines)
        else:
            # 2) 문단 단위로 찾기
            paragraphs = result.split('\n\n')
            paragraphs, found = _find_and_replace_paragraph(paragraphs, snippet_key, snippet, new_text)
            
            if found:
                result = '\n\n'.join(paragraphs)
            else:
                # 3) 찾지 못하면 끝에 추가
                result = f"{result.rstrip()}\n\n{new_text}"
    
    return result


# ============================================================
# ADD 처리 헬퍼 함수
# ============================================================

def _process_add_markers(content: str, changes: str) -> str:
    """
    [ADD] 마커를 찾아서 새 내용 추가
    
    Args:
        content: 원본 텍스트
        changes: 변경사항 (마커 포함)
    
    Returns:
        추가 처리된 텍스트
    """
    add_pattern = re.compile(r'\[ADD\]\s*\n*([^\[]*?)(?=\[|$)', re.DOTALL)
    add_matches = add_pattern.findall(changes)
    
    result = content
    
    for add_content in add_matches:
        new_text = add_content.strip()
        if new_text:
            result = f"{result.rstrip()}\n\n{new_text}"
    
    return result


# ============================================================
# 메인 병합 함수
# ============================================================

def merge_section_changes(old_content: str, changes: str) -> str:
    """
    섹션 변경사항을 기존 내용과 병합
    
    처리 순서:
    1. [DELETE: ...] - 기존 내용 삭제
    2. [UPDATE: ...] - 기존 내용 교체
    3. [ADD] - 새 내용 추가
    
    Args:
        old_content: 기존 섹션 내용
        changes: LLM이 생성한 변경사항 (마커 포함)
    
    Returns:
        병합된 최종 텍스트
    """
    # 변경사항이 없는 경우
    if not changes or '[NO_CHANGE]' in changes:
        return old_content
    
    # 기존 내용이 없는 경우 (새 섹션)
    if not old_content.strip():
        cleaned = changes.replace('[ADD]', '').replace('[UPDATE:', '').replace('[DELETE:', '').strip()
        cleaned = re.sub(r'\[UPDATE:[^\]]*\]', '', cleaned)
        cleaned = re.sub(r'\[DELETE:[^\]]*\]', '', cleaned)
        return cleaned.strip()
    
    # 1단계: DELETE 처리
    result = _process_delete_markers(old_content, changes)
    
    # 2단계: UPDATE 처리
    result = _process_update_markers(result, changes)
    
    # 3단계: ADD 처리
    result = _process_add_markers(result, changes)
    
    return result.strip()
