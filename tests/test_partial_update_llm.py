import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure fastapi module path
sys.path.append('c:/ChungAngUniversity/3_2/CapstoneDesign/CICDAutoDoc1031/fastapi')

from domain.langgraph.document_state import DocumentState
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from langchain_openai import ChatOpenAI


def build_state() -> DocumentState:
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

    return {
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


def main():
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('[LLM TEST] OPENAI_API_KEY not set. Please set it and re-run.')
        return

    # Use smaller/cheaper model for testing if available
    model_name = os.getenv('DOC_SUMMARIZER_MODEL', 'gpt-4o-mini')
    llm = ChatOpenAI(model=model_name, temperature=0.2)

    os.environ['PARTIAL_UPDATE_MAX_CONCURRENCY'] = '4'

    state = build_state()

    # Run analyzer with real LLM (SECTION_TARGETS may be inferred or parsed)
    state = change_analyzer_node(state, llm=llm, use_mock=False)
    print('[LLM TEST] analysis_result:', state.get('analysis_result')[:500] if state.get('analysis_result') else None)
    print('[LLM TEST] target_doc_sections:', state.get('target_doc_sections'))

    # Run document generator (partial update with real LLM)
    state = document_generator_node(state, llm=llm, use_mock=False)
    print('[LLM TEST] status:', state.get('status'))
    print('[LLM TEST] updated_sections:', state.get('updated_sections'))
    content = state.get('document_content') or ''
    print('\n[LLM TEST] Document Preview (first 600 chars):\n')
    print(content[:600])


if __name__ == '__main__':
    main()
