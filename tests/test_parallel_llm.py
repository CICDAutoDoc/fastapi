import time
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# 프로젝트 루트를 sys.path에 추가
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from domain.langgraph.document_state import DocumentState


def _run_change_analyzer_llm_test():
    print("[LLM TEST] change_analyzer_node: FILE_SUMMARY_MAX_CONCURRENCY effect")
    
    # 실제 diff 내용
    diff = """diff --git a/app/endpoints/chat.py b/app/endpoints/chat.py
index 1234567..abcdefg 100644
--- a/app/endpoints/chat.py
+++ b/app/endpoints/chat.py
@@ -10,6 +10,8 @@ from app.services import ChatService
 
 async def chat_endpoint(message: str):
     service = ChatService()
+    # Add validation
+    if not message:
+        raise ValueError("Message cannot be empty")
     return await service.process(message)

diff --git a/app/services/chat_service.py b/app/services/chat_service.py
index 2345678..bcdefgh 100644
--- a/app/services/chat_service.py
+++ b/app/services/chat_service.py
@@ -5,6 +5,9 @@ class ChatService:
     
     async def process(self, message: str):
         result = await self.llm.invoke(message)
+        # Add logging
+        logger.info(f"Processed: {message[:50]}")
         return result

diff --git a/app/models/chat.py b/app/models/chat.py
index 3456789..cdefghi 100644
--- a/app/models/chat.py
+++ b/app/models/chat.py
@@ -3,6 +3,7 @@ from pydantic import BaseModel
 class ChatMessage(BaseModel):
     content: str
     timestamp: datetime
+    user_id: str
"""
    
    files = [
        "app/endpoints/chat.py",
        "app/services/chat_service.py",
        "app/models/chat.py",
    ]
    
    state = DocumentState({
        "diff_content": diff,
        "changed_files": files,
        "code_change": {"commit_message": "Add validation and logging to chat endpoints"}
    })

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    # Sequential
    print("\n=== Sequential (CONCURRENCY=1) ===")
    os.environ["FILE_SUMMARY_MAX_CONCURRENCY"] = "1"
    t0 = time.time()
    s1 = change_analyzer_node(state.copy(), llm=llm, use_mock=False)
    dur_seq = time.time() - t0
    print(f"Duration: {dur_seq:.2f}s")
    print(f"Summaries generated: {len(s1.get('file_change_summaries', []))}")
    for summary in s1.get('file_change_summaries', [])[:2]:
        print(f"  - {summary['file']}: {summary['summary'][:80]}")

    # Parallel
    print("\n=== Parallel (CONCURRENCY=3) ===")
    os.environ["FILE_SUMMARY_MAX_CONCURRENCY"] = "3"
    t1 = time.time()
    s2 = change_analyzer_node(state.copy(), llm=llm, use_mock=False)
    dur_par = time.time() - t1
    print(f"Duration: {dur_par:.2f}s")
    print(f"Summaries generated: {len(s2.get('file_change_summaries', []))}")
    for summary in s2.get('file_change_summaries', [])[:2]:
        print(f"  - {summary['file']}: {summary['summary'][:80]}")

    speedup = dur_seq / dur_par if dur_par > 0 else 0
    print(f"\n🚀 Speedup: {speedup:.2f}x (Sequential: {dur_seq:.2f}s → Parallel: {dur_par:.2f}s)")


def _run_document_generator_llm_test():
    print("\n" + "="*80)
    print("[LLM TEST] document_generator_node: PARTIAL_UPDATE_MAX_CONCURRENCY effect")
    
    existing_md = """# Chat Service Documentation

## Overview
This is a chat service that provides real-time messaging capabilities.

## Architecture
The service follows a standard three-tier architecture with endpoints, services, and models.

## Modules
- **Endpoints**: Handle HTTP requests
- **Services**: Business logic layer
- **Models**: Data models

## Changelog
- 2024-11-01: Initial release
"""
    
    state = DocumentState({
        "should_update": True,
        "existing_document": {"content": existing_md, "title": "Chat Service Documentation"},
        "analysis_result": "Added validation and logging features to chat endpoints",
        "changed_files": ["app/endpoints/chat.py", "app/services/chat_service.py"],
        "file_change_summaries": [
            {"file": "app/endpoints/chat.py", "summary": "Added message validation", "priority": "high"},
            {"file": "app/services/chat_service.py", "summary": "Added logging", "priority": "high"},
        ],
        "code_change": {"commit_message": "Add validation and logging"},
        "target_doc_sections": ["overview", "modules", "changelog"],
    })

    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)

    # Sequential
    print("\n=== Sequential (CONCURRENCY=1) ===")
    os.environ["PARTIAL_UPDATE_MAX_CONCURRENCY"] = "1"
    t0 = time.time()
    s1 = document_generator_node(state.copy(), llm=llm, use_mock=False)
    dur_seq = time.time() - t0
    print(f"Duration: {dur_seq:.2f}s")
    print(f"Updated sections: {len(s1.get('updated_sections', []))}")

    # Parallel
    print("\n=== Parallel (CONCURRENCY=3) ===")
    os.environ["PARTIAL_UPDATE_MAX_CONCURRENCY"] = "3"
    t1 = time.time()
    s2 = document_generator_node(state.copy(), llm=llm, use_mock=False)
    dur_par = time.time() - t1
    print(f"Duration: {dur_par:.2f}s")
    print(f"Updated sections: {len(s2.get('updated_sections', []))}")

    speedup = dur_seq / dur_par if dur_par > 0 else 0
    print(f"\n🚀 Speedup: {speedup:.2f}x (Sequential: {dur_seq:.2f}s → Parallel: {dur_par:.2f}s)")


if __name__ == "__main__":
    # API 키 확인
    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        sys.exit(1)
    
    print("="*80)
    print("LLM Parallel Processing Test (실제 OpenAI API 사용)")
    print("="*80)
    
    _run_change_analyzer_llm_test()
    _run_document_generator_llm_test()
    
    print("\n" + "="*80)
    print("✅ All LLM parallel tests completed.")
    print("="*80)
