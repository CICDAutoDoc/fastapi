"""
마크다운 섹션 파싱 모듈

마크다운 문서를 섹션별로 파싱하고 병합하는 기능을 제공합니다.
"""

import re
from typing import Dict, List
from dataclasses import dataclass


# 섹션 키 매핑 (기존 로직 유지)
SECTION_KEY_MAP = {
    'overview': ['project overview', 'overview'],
    'architecture': ['architecture', 'system design'],
    'diagram': ['architecture diagram', 'system diagram', 'diagram'],
    'modules': ['key modules', 'modules'],
    'changelog': ['changelog', 'change log', 'recent changes'],
}


@dataclass
class ParsedDocument:
    """파싱된 문서 구조"""
    sections: Dict[str, str]
    order: List[str]
    headings: Dict[str, str]


def normalize_section_key(heading: str) -> str:
    """섹션 제목을 정규화된 키로 변환"""
    lower = heading.lower()
    for key, variants in SECTION_KEY_MAP.items():
        if any(v in lower for v in variants):
            return key
    return re.sub(r'[^a-z0-9]+', '_', lower).strip('_')[:40]


def parse_markdown_sections(content: str) -> ParsedDocument:
    """마크다운을 섹션별로 파싱하되, 지정된 H2 제목만 섹션으로 인정"""
    # 허용되는 섹션 제목 (대소문자/공백 차이 무시)
    allowed_titles = {
        'project overview',
        'architecture',
        'architecture diagram',
        'key modules',
        'changelog',
    }

    pattern = re.compile(r'^##\s+(.+)$', re.MULTILINE)
    matches = list(pattern.finditer(content))
    # H2 중 허용된 제목만 필터링
    filtered = []
    for m in matches:
        heading_raw = m.group(1).strip()
        heading_norm = re.sub(r'\s+', ' ', heading_raw).strip().lower()
        if heading_norm in allowed_titles:
            filtered.append(m)

    if not filtered:
        return ParsedDocument(sections={'__full__': content}, order=['__full__'], headings={'__full__': 'Document'})
    
    sections: Dict[str, str] = {}
    order: List[str] = []
    headings: Dict[str, str] = {}
    
    for idx, m in enumerate(filtered):
        heading = m.group(1).strip()
        start = m.end()
        end = filtered[idx + 1].start() if idx + 1 < len(filtered) else len(content)
        body = content[start:end].strip()
        # 허용된 제목은 고정 키 매핑으로 사용
        lower = re.sub(r'\s+', ' ', heading).strip().lower()
        if lower == 'project overview':
            key = 'overview'
        elif lower == 'architecture':
            key = 'architecture'
        elif lower == 'architecture diagram':
            key = 'diagram'
        elif lower == 'key modules':
            key = 'modules'
        elif lower == 'changelog':
            key = 'changelog'
        else:
            # 이 케이스는 발생하지 않지만 안전망으로 기존 로직 유지
            key = normalize_section_key(heading)
        
        # 중복 키 방지
        unique_key = key
        suffix = 2
        while unique_key in sections:
            unique_key = f"{key}_{suffix}"
            suffix += 1
        
        sections[unique_key] = body
        order.append(unique_key)
        headings[unique_key] = heading
    
    return ParsedDocument(sections=sections, order=order, headings=headings)


def merge_sections(parsed: ParsedDocument, updated: Dict[str, str]) -> str:
    """업데이트된 섹션만 교체하고 나머지는 원본 유지"""
    lines: List[str] = []
    for key in parsed.order:
        original_heading = parsed.headings.get(key, key.replace('_', ' ').title())
        body = updated.get(key, parsed.sections.get(key, ''))
        lines.append(f"## {original_heading}\n{body.strip()}\n")
    return "\n".join(lines).strip()
