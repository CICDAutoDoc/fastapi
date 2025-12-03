"""
간단한 LLM 테스트 - 파일 요약 기능만 집중 테스트
"""

import sys
import os
from dotenv import load_dotenv

load_dotenv()
sys.path.append('.')

from langchain_openai import ChatOpenAI
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.document_state import DocumentState


def simple_llm_test():
    """최소한의 LLM 테스트"""
    print("\n🧪 Simple LLM Test for File Summaries")
    print("=" * 70)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return
    
    print(f"✅ API Key loaded")
    
    # LLM 초기화
    llm = ChatOpenAI(
        api_key=api_key,
        model="gpt-4o-mini",
        temperature=0.1,
        timeout=30
    )
    print("✅ LLM initialized (gpt-4o-mini, timeout=30s)")
    
    # 간단한 변경사항 (2개 파일만)
    state: DocumentState = {
        "code_change_id": 1,
        "status": "analyzing",
        "changed_files": [
            "src/api/auth_router.py",
            "tests/test_auth.py"
        ],
        "diff_content": """
diff --git a/src/api/auth_router.py b/src/api/auth_router.py
+@router.post("/login")
+def login(credentials: LoginRequest):
+    return {"token": "abc123"}

diff --git a/tests/test_auth.py b/tests/test_auth.py
+def test_login():
+    assert True
        """,
        "code_change": {
            "commit_sha": "abc123",
            "commit_message": "Add basic login endpoint"
        }
    }
    
    print(f"\n📋 Testing with {len(state['changed_files'])} files...")
    print(f"   Files: {state['changed_files']}")
    
    try:
        # Change Analyzer 실행
        print("\n⏳ Calling LLM API (this may take 10-20 seconds)...")
        result_state = change_analyzer_node(state, llm=llm, use_mock=False)
        
        print("\n✅ LLM API call successful!")
        print(f"   Status: {result_state.get('status')}")
        
        # file_change_summaries 확인
        if "file_change_summaries" in result_state:
            summaries = result_state["file_change_summaries"]
            print(f"\n📝 Generated {len(summaries)} file summaries:")
            print("-" * 70)
            
            for i, summary in enumerate(summaries, 1):
                print(f"\n{i}. {summary['file']}")
                print(f"   Priority: {summary['priority']}")
                print(f"   Summary: {summary['summary']}")
        else:
            print("⚠️  No file_change_summaries in result")
        
        # analysis_result 확인
        if "analysis_result" in result_state:
            print(f"\n📊 Analysis Result:")
            print("-" * 70)
            print(result_state["analysis_result"])
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    simple_llm_test()
