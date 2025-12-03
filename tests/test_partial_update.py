import sys
from typing import Any

# Adjust path if needed
sys.path.append('c:/ChungAngUniversity/3_2/CapstoneDesign/CICDAutoDoc1031/fastapi')

from domain.langgraph.document_state import DocumentState
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
import os


class FakeLLM:
    class Resp:
        def __init__(self, text: str):
            self.content = text

    def invoke(self, messages):
        # Inspect last user message to detect changelog vs normal section
        last = messages[-1].content if messages else ''
        if isinstance(last, list):
            last = '\n'.join(str(c) for c in last)
        txt = str(last).lower()
        if '현재 섹션: changelog' in txt or 'changelog' in txt:
            return self.Resp('- auto: test change entry')
        return self.Resp('[ADD]\nAuto-added note from FakeLLM')


def build_mock_state() -> DocumentState:
    existing_md = """# Project Documentation

## Project Overview
Initial overview text.

## Architecture
Service A -> Service B

## Key Modules
- module-x: does X
- module-y: does Y

## Changelog
- Initial release
"""

    # Unified diff for a file change
    diff = """--- a/app/endpoints/chat.py
+++ b/app/endpoints/chat.py
@@ -1,3 +1,6 @@
-from fastapi import APIRouter
+from fastapi import APIRouter, Depends
+from .service import ChatService
+
 router = APIRouter()
+svc = ChatService()
"""

    state: DocumentState = {
        'code_change_id': 1,
        'code_change': {
            'commit_sha': 'abc123456789',
            'commit_message': 'feat(chat): add streaming endpoint and service'
        },
        'diff_content': diff,
        'changed_files': ['app/endpoints/chat.py'],
        'existing_document': {
            'title': 'Project Documentation',
            'content': existing_md
        },
        'should_update': True,
        'status': 'analyzing'
    }
    return state


def run_test(use_mock: bool = True, use_fake_llm: bool = False) -> None:
    state = build_mock_state()
    # Run change analyzer
    state = change_analyzer_node(state, llm=None, use_mock=use_mock)
    print('[TEST] analysis_result length:', len(state.get('analysis_result') or ''))
    print('[TEST] target_doc_sections:', state.get('target_doc_sections'))
    print('[TEST] file_change_summaries:', state.get('file_change_summaries'))

    # Run document generator (partial update expected)
    # Enable parallel processing and use FakeLLM to trigger non-mock path
    os.environ['PARTIAL_UPDATE_MAX_CONCURRENCY'] = '4'
    llm = FakeLLM() if use_fake_llm else None
    state = document_generator_node(state, llm=llm, use_mock=False)
    print('[TEST] status:', state.get('status'))
    print('[TEST] updated_sections:', state.get('updated_sections'))
    content = state.get('document_content') or ''
    assert '## Project Overview' in content
    assert '## Architecture' in content
    assert '## Key Modules' in content
    assert '## Changelog' in content
    print('[TEST] document_content length:', len(content))
    print('\n[TEST] Final Document Preview:\n')
    print(content[:500])


if __name__ == '__main__':
    run_test(use_mock=True, use_fake_llm=True)
