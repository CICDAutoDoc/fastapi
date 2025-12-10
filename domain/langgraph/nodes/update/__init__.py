"""
문서 업데이트 모듈

이 모듈은 document_generator_node의 기능을 분리하여 
가독성과 유지보수성을 향상시킵니다.
"""

from .section_parser import (
    ParsedDocument,
    parse_markdown_sections,
    normalize_section_key,
    merge_sections,
    SECTION_KEY_MAP
)

from .section_updater import (
    update_section_llm,
    update_section_mock,
    infer_target_sections
)

from .prompt_builder import build_section_prompt

from .content_merger import (
    merge_changelog,
    merge_section_changes
)

from .partial_update_handler import handle_partial_update

__all__ = [
    'ParsedDocument',
    'parse_markdown_sections',
    'normalize_section_key',
    'merge_sections',
    'SECTION_KEY_MAP',
    'update_section_llm',
    'update_section_mock',
    'infer_target_sections',
    'build_section_prompt',
    'merge_changelog',
    'merge_section_changes',
    'handle_partial_update',
]
