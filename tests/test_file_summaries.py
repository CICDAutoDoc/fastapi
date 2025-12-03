"""
File Summaries 기능 테스트

변경된 코드:
1. change_analyzer_node에서 file_change_summaries 생성
2. document_generator_node에서 file_summaries 사용
"""

import sys
sys.path.append('.')

from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from domain.langgraph.document_state import DocumentState


def test_file_summaries_generation():
    """change_analyzer가 file_change_summaries를 생성하는지 테스트"""
    print("\n🧪 Test 1: File Summaries Generation")
    print("=" * 70)
    
    # 여러 파일이 변경된 상황 시뮬레이션
    state: DocumentState = {
        "code_change_id": 1,
        "status": "analyzing",
        "changed_files": [
            "src/api/auth_router.py",          # high priority (router)
            "src/models/user_schema.py",       # high priority (schema)
            "src/utils/helper.py",             # medium priority (util)
            "README.md",                        # low priority
            "tests/test_auth.py"               # medium priority (test)
        ],
        "diff_content": """
diff --git a/src/api/auth_router.py b/src/api/auth_router.py
index 1234567..abcdefg 100644
--- a/src/api/auth_router.py
+++ b/src/api/auth_router.py
@@ -10,5 +10,12 @@ from fastapi import APIRouter
+@router.post("/login")
+def login(credentials: LoginRequest):
+    return authenticate_user(credentials)

diff --git a/src/models/user_schema.py b/src/models/user_schema.py
index 2345678..bcdefgh 100644
--- a/src/models/user_schema.py
+++ b/src/models/user_schema.py
@@ -5,3 +5,8 @@ class UserSchema(BaseModel):
+class LoginRequest(BaseModel):
+    username: str
+    password: str
        """,
        "code_change": {
            "commit_sha": "abc1234",
            "commit_message": "Add login endpoint and authentication"
        }
    }
    
    # Change Analyzer 실행 (Mock 모드)
    result_state = change_analyzer_node(state, llm=None, use_mock=True)
    
    # file_change_summaries가 생성되었는지 확인
    print("\n📊 Results:")
    print(f"  Status: {result_state.get('status')}")
    print(f"  Has file_change_summaries: {'file_change_summaries' in result_state}")
    
    if "file_change_summaries" in result_state:
        summaries = result_state["file_change_summaries"]
        print(f"  Number of summaries: {len(summaries)}")
        print(f"\n📝 File Summaries:")
        
        for i, summary in enumerate(summaries, 1):
            print(f"\n  {i}. File: {summary['file']}")
            print(f"     Priority: {summary['priority']}")
            print(f"     Change Type: {summary['change_type']}")
            print(f"     Summary: {summary['summary'][:80]}...")
    
    assert "file_change_summaries" in result_state, "file_change_summaries not generated!"
    assert len(result_state["file_change_summaries"]) == 5, "Should have 5 file summaries"
    
    # 우선순위 검증
    summaries = result_state["file_change_summaries"]
    router_summary = next((s for s in summaries if "auth_router" in s['file']), None)
    schema_summary = next((s for s in summaries if "user_schema" in s['file']), None)
    util_summary = next((s for s in summaries if "helper" in s['file']), None)
    readme_summary = next((s for s in summaries if "README" in s['file']), None)
    
    assert router_summary['priority'] == 'high', "Router should be high priority"
    assert schema_summary['priority'] == 'high', "Schema should be high priority"
    assert util_summary['priority'] == 'medium', "Util should be medium priority"
    assert readme_summary['priority'] == 'low', "README should be low priority"
    
    print("\n✅ All assertions passed!")
    return result_state


def test_document_generator_uses_summaries():
    """document_generator가 file_summaries를 사용하는지 테스트"""
    print("\n\n🧪 Test 2: Document Generator Using File Summaries")
    print("=" * 70)
    
    # 먼저 file_summaries를 가진 state 생성
    state: DocumentState = {
        "code_change_id": 1,
        "status": "generating",
        "should_update": True,
        "changed_files": [
            "src/api/auth_router.py",
            "src/models/user_schema.py"
        ],
        "file_change_summaries": [
            {
                "file": "src/api/auth_router.py",
                "priority": "high",
                "change_type": "modified",
                "summary": "Added new login endpoint with POST /api/auth/login"
            },
            {
                "file": "src/models/user_schema.py",
                "priority": "high",
                "change_type": "modified",
                "summary": "Created LoginRequest schema for authentication"
            }
        ],
        "analysis_result": "Added authentication system with login endpoint",
        "existing_document": {
            "content": """# API Documentation

## Overview
Basic API structure

## Modules

### Authentication
- Basic auth setup

## Changelog
- 2024-01-01: Initial version
"""
        },
        "code_change": {
            "commit_sha": "abc1234",
            "commit_message": "Add login endpoint"
        },
        "target_doc_sections": ["modules", "changelog"]
    }
    
    # Document Generator 실행 (Mock 모드)
    result_state = document_generator_node(state, llm=None, use_mock=True)
    
    print("\n📊 Results:")
    print(f"  Status: {result_state.get('status')}")
    print(f"  Has document_content: {'document_content' in result_state}")
    
    if "document_content" in result_state:
        content = result_state["document_content"]
        print(f"  Document length: {len(content)} chars")
        print(f"\n📄 Document Preview (first 500 chars):")
        print(content[:500])
        print("...")
    
    assert "document_content" in result_state, "Document not generated!"
    assert result_state["status"] == "saving", "Status should be 'saving'"
    
    print("\n✅ Document generator successfully used file summaries!")
    return result_state


def test_full_integration():
    """전체 통합 테스트: change_analyzer -> document_generator"""
    print("\n\n🧪 Test 3: Full Integration Test")
    print("=" * 70)
    
    # 1. 초기 state
    initial_state: DocumentState = {
        "code_change_id": 1,
        "status": "analyzing",
        "should_update": True,
        "changed_files": [
            "src/api/payment_router.py",
            "src/services/payment_service.py",
            "src/models/payment_schema.py",
            "tests/test_payment.py",
            "README.md"
        ],
        "diff_content": "..." * 100,  # Simulated large diff
        "existing_document": {
            "content": """# Payment System

## Overview
Payment processing system

## Changelog
- Initial version
"""
        },
        "code_change": {
            "commit_sha": "xyz7890",
            "commit_message": "Implement payment processing with Stripe integration"
        }
    }
    
    print("\n📋 Step 1: Running change_analyzer_node...")
    # 2. Change Analyzer 실행
    analyzed_state = change_analyzer_node(initial_state, llm=None, use_mock=True)
    
    print(f"  ✅ Analysis complete")
    print(f"  - Status: {analyzed_state['status']}")
    print(f"  - File summaries created: {len(analyzed_state.get('file_change_summaries', []))}")
    print(f"  - Target sections: {analyzed_state.get('target_doc_sections', [])}")
    
    # 3. Document Generator 실행
    print("\n📋 Step 2: Running document_generator_node...")
    final_state = document_generator_node(analyzed_state, llm=None, use_mock=True)
    
    print(f"  ✅ Document generation complete")
    print(f"  - Status: {final_state['status']}")
    print(f"  - Document length: {len(final_state.get('document_content', ''))} chars")
    print(f"  - Summary: {final_state.get('document_summary', 'N/A')}")
    
    # 검증
    assert "file_change_summaries" in analyzed_state
    assert len(analyzed_state["file_change_summaries"]) == 5
    assert "document_content" in final_state
    assert final_state["status"] == "saving"
    
    # 우선순위별 요약 개수 확인
    summaries = analyzed_state["file_change_summaries"]
    high_priority = [s for s in summaries if s['priority'] == 'high']
    medium_priority = [s for s in summaries if s['priority'] == 'medium']
    low_priority = [s for s in summaries if s['priority'] == 'low']
    
    print(f"\n📊 Priority Distribution:")
    print(f"  - High priority: {len(high_priority)} files")
    print(f"    {[s['file'] for s in high_priority]}")
    print(f"  - Medium priority: {len(medium_priority)} files")
    print(f"    {[s['file'] for s in medium_priority]}")
    print(f"  - Low priority: {len(low_priority)} files")
    print(f"    {[s['file'] for s in low_priority]}")
    
    print("\n✅ Full integration test passed!")
    print("\n" + "=" * 70)
    print("🎉 All file summary tests completed successfully!")


if __name__ == "__main__":
    # 테스트 실행
    state1 = test_file_summaries_generation()
    state2 = test_document_generator_uses_summaries()
    test_full_integration()
