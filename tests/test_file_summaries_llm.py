"""
File Summaries 기능 LLM 모드 테스트

실제 OpenAI API를 사용하여 파일 요약 기능을 테스트합니다.
"""

import sys
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

sys.path.append('.')

from langchain_openai import ChatOpenAI
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from domain.langgraph.document_state import DocumentState


def test_file_summaries_with_llm():
    """LLM을 사용한 파일 요약 생성 테스트"""
    print("\n🧪 Test: File Summaries with LLM")
    print("=" * 70)
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found in environment variables")
        return
    
    print(f"✅ API Key found: {api_key[:8]}...")
    
    # LLM 초기화
    llm = ChatOpenAI(
        api_key=api_key,
        model="gpt-4o-mini",
        temperature=0.1
    )
    print("✅ LLM initialized")
    
    # 실제 코드 변경사항 시뮬레이션
    state: DocumentState = {
        "code_change_id": 1,
        "status": "analyzing",
        "changed_files": [
            "src/api/payment_router.py",
            "src/services/stripe_service.py",
            "src/models/payment_schema.py",
            "tests/test_payment.py",
            "README.md"
        ],
        "diff_content": """
diff --git a/src/api/payment_router.py b/src/api/payment_router.py
index 1234567..abcdefg 100644
--- a/src/api/payment_router.py
+++ b/src/api/payment_router.py
@@ -1,5 +1,30 @@
 from fastapi import APIRouter, Depends, HTTPException
+from src.services.stripe_service import StripeService
+from src.models.payment_schema import PaymentRequest, PaymentResponse
 
 router = APIRouter(prefix="/api/payment", tags=["payment"])
+
+@router.post("/create", response_model=PaymentResponse)
+async def create_payment(
+    payment: PaymentRequest,
+    stripe_service: StripeService = Depends()
+):
+    \"\"\"
+    Create a new payment with Stripe integration
+    
+    Args:
+        payment: Payment request with amount and currency
+        stripe_service: Injected Stripe service
+        
+    Returns:
+        PaymentResponse with payment intent ID and status
+    \"\"\"
+    try:
+        result = await stripe_service.create_payment_intent(
+            amount=payment.amount,
+            currency=payment.currency
+        )
+        return PaymentResponse(
+            payment_id=result.id,
+            status=result.status,
+            client_secret=result.client_secret
+        )
+    except Exception as e:
+        raise HTTPException(status_code=400, detail=str(e))

diff --git a/src/services/stripe_service.py b/src/services/stripe_service.py
new file mode 100644
index 0000000..2345678
--- /dev/null
+++ b/src/services/stripe_service.py
@@ -0,0 +1,25 @@
+import stripe
+from typing import Dict, Any
+
+class StripeService:
+    \"\"\"Stripe payment processing service\"\"\"
+    
+    def __init__(self, api_key: str):
+        stripe.api_key = api_key
+        
+    async def create_payment_intent(
+        self, 
+        amount: int, 
+        currency: str = "usd"
+    ) -> Any:
+        \"\"\"
+        Create a Stripe payment intent
+        
+        Args:
+            amount: Amount in cents
+            currency: Currency code (default: usd)
+            
+        Returns:
+            Stripe PaymentIntent object
+        \"\"\"
+        return stripe.PaymentIntent.create(
+            amount=amount,
+            currency=currency,
+            payment_method_types=["card"]
+        )

diff --git a/src/models/payment_schema.py b/src/models/payment_schema.py
index 3456789..bcdefgh 100644
--- a/src/models/payment_schema.py
+++ b/src/models/payment_schema.py
@@ -1,5 +1,20 @@
 from pydantic import BaseModel, Field
+from typing import Optional
 
 class PaymentRequest(BaseModel):
-    pass
+    amount: int = Field(..., description="Payment amount in cents", gt=0)
+    currency: str = Field(default="usd", description="Currency code")
+    
+    class Config:
+        json_schema_extra = {
+            "example": {
+                "amount": 1000,
+                "currency": "usd"
+            }
+        }
+
+class PaymentResponse(BaseModel):
+    payment_id: str
+    status: str
+    client_secret: Optional[str] = None
        """,
        "code_change": {
            "commit_sha": "abc123def456",
            "commit_message": "feat: Implement Stripe payment integration with create payment endpoint"
        }
    }
    
    print("\n📋 Running change_analyzer_node with LLM...")
    print(f"  Changed files: {len(state['changed_files'])}")
    print(f"  Diff size: {len(state['diff_content'])} chars")
    
    # Change Analyzer 실행 (LLM 모드)
    result_state = change_analyzer_node(state, llm=llm, use_mock=False)
    
    print(f"\n✅ Analysis complete!")
    print(f"  Status: {result_state.get('status')}")
    print(f"  Has file_change_summaries: {'file_change_summaries' in result_state}")
    
    if "file_change_summaries" in result_state:
        summaries = result_state["file_change_summaries"]
        print(f"  Number of summaries: {len(summaries)}")
        
        print(f"\n📝 LLM-Generated File Summaries:")
        print("-" * 70)
        
        for i, summary in enumerate(summaries, 1):
            print(f"\n{i}. 📄 {summary['file']}")
            print(f"   Priority: {summary['priority']}")
            print(f"   Change Type: {summary['change_type']}")
            print(f"   Summary: {summary['summary']}")
    
    # Analysis result 확인
    if "analysis_result" in result_state:
        print(f"\n📊 Analysis Result:")
        print("-" * 70)
        print(result_state["analysis_result"])
    
    # Target sections 확인
    if "target_doc_sections" in result_state:
        print(f"\n🎯 Target Doc Sections:")
        print(f"   {result_state['target_doc_sections']}")
    
    # 검증
    assert "file_change_summaries" in result_state, "file_change_summaries not generated!"
    assert len(result_state["file_change_summaries"]) == 5, "Should have 5 file summaries"
    
    # 우선순위 검증
    summaries = result_state["file_change_summaries"]
    high_priority = [s for s in summaries if s['priority'] == 'high']
    medium_priority = [s for s in summaries if s['priority'] == 'medium']
    low_priority = [s for s in summaries if s['priority'] == 'low']
    
    print(f"\n📊 Priority Distribution:")
    print(f"   High: {len(high_priority)} files")
    for s in high_priority:
        print(f"     - {s['file']}")
    print(f"   Medium: {len(medium_priority)} files")
    for s in medium_priority:
        print(f"     - {s['file']}")
    print(f"   Low: {len(low_priority)} files")
    for s in low_priority:
        print(f"     - {s['file']}")
    
    print("\n✅ All assertions passed!")
    return result_state


def test_document_generator_with_llm():
    """LLM을 사용한 문서 생성 테스트"""
    print("\n\n🧪 Test: Document Generator with LLM")
    print("=" * 70)
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return
    
    # LLM 초기화
    llm = ChatOpenAI(
        api_key=api_key,
        model="gpt-4o-mini",
        temperature=0.1
    )
    
    # 먼저 change_analyzer로 file_summaries 생성
    print("\n📋 Step 1: Generating file summaries with LLM...")
    
    initial_state: DocumentState = {
        "code_change_id": 1,
        "status": "analyzing",
        "changed_files": [
            "src/api/auth_router.py",
            "src/services/jwt_service.py"
        ],
        "diff_content": """
diff --git a/src/api/auth_router.py b/src/api/auth_router.py
+@router.post("/login")
+def login(credentials: LoginRequest):
+    token = jwt_service.generate_token(credentials.username)
+    return {"access_token": token}

diff --git a/src/services/jwt_service.py b/src/services/jwt_service.py
+def generate_token(username: str) -> str:
+    return jwt.encode({"sub": username}, SECRET_KEY)
        """,
        "code_change": {
            "commit_sha": "xyz789",
            "commit_message": "Add JWT authentication system"
        }
    }
    
    analyzed_state = change_analyzer_node(initial_state, llm=llm, use_mock=False)
    
    print(f"✅ File summaries generated: {len(analyzed_state.get('file_change_summaries', []))}")
    
    # 문서 업데이트 시나리오
    print("\n📋 Step 2: Generating document with LLM...")
    
    analyzed_state.update({
        "should_update": True,
        "existing_document": {
            "content": """# API Documentation

## Overview
FastAPI application for user management.

## Modules

### User Management
- User CRUD operations
- Profile management

## Changelog
- 2024-01-01: Initial version
"""
        },
        "target_doc_sections": ["modules", "changelog"]
    })
    
    final_state = document_generator_node(analyzed_state, llm=llm, use_mock=False)
    
    print(f"\n✅ Document generation complete!")
    print(f"  Status: {final_state.get('status')}")
    print(f"  Document length: {len(final_state.get('document_content', ''))} chars")
    
    if "document_content" in final_state:
        print(f"\n📄 Generated Document:")
        print("=" * 70)
        print(final_state["document_content"])
        print("=" * 70)
    
    if "document_summary" in final_state:
        print(f"\n📝 Document Summary:")
        print(final_state["document_summary"])
    
    assert "document_content" in final_state, "Document not generated!"
    assert final_state["status"] == "saving", "Status should be 'saving'"
    
    print("\n✅ All assertions passed!")
    return final_state


def test_full_integration_with_llm():
    """전체 통합 테스트 (LLM 모드)"""
    print("\n\n🧪 Test: Full Integration with LLM")
    print("=" * 70)
    
    # API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY not found")
        return
    
    print("✅ Starting full integration test with real LLM...")
    
    # LLM 초기화
    llm = ChatOpenAI(
        api_key=api_key,
        model="gpt-4o-mini",
        temperature=0.1
    )
    
    # 복잡한 변경사항 시뮬레이션
    state: DocumentState = {
        "code_change_id": 1,
        "status": "analyzing",
        "should_update": True,
        "changed_files": [
            "src/api/payment_router.py",
            "src/services/payment_service.py",
            "src/models/payment_schema.py",
            "tests/test_payment.py"
        ],
        "diff_content": "+" * 500,  # Large diff
        "existing_document": {
            "content": """# Payment System Documentation

## Overview
Payment processing system

## Architecture
Basic structure

## Modules
Initial modules

## Changelog
- Initial version
"""
        },
        "code_change": {
            "commit_sha": "abc123",
            "commit_message": "feat: Add Stripe integration with webhook support"
        }
    }
    
    print("\n📋 Step 1: Analyzing changes with LLM...")
    analyzed_state = change_analyzer_node(state, llm=llm, use_mock=False)
    
    print(f"  ✅ Analysis complete")
    print(f"     File summaries: {len(analyzed_state.get('file_change_summaries', []))}")
    print(f"     Target sections: {analyzed_state.get('target_doc_sections', [])}")
    
    print("\n📋 Step 2: Generating document with LLM...")
    final_state = document_generator_node(analyzed_state, llm=llm, use_mock=False)
    
    print(f"  ✅ Document generated")
    print(f"     Status: {final_state['status']}")
    print(f"     Length: {len(final_state.get('document_content', ''))} chars")
    
    # 결과 출력
    if "file_change_summaries" in analyzed_state:
        print(f"\n📝 File Summaries (LLM-generated):")
        for s in analyzed_state["file_change_summaries"]:
            print(f"  - {s['file']} ({s['priority']}): {s['summary'][:60]}...")
    
    if "document_content" in final_state:
        print(f"\n📄 Final Document Preview:")
        print("-" * 70)
        print(final_state["document_content"][:800])
        print("\n... (truncated)")
        print("-" * 70)
    
    # 검증
    assert "file_change_summaries" in analyzed_state
    assert "document_content" in final_state
    assert final_state["status"] == "saving"
    
    print("\n✅ Full integration test passed!")
    print("\n" + "=" * 70)
    print("🎉 All LLM tests completed successfully!")


if __name__ == "__main__":
    try:
        # 테스트 실행
        print("\n🚀 Starting LLM Mode Tests")
        print("=" * 70)
        
        test_file_summaries_with_llm()
        test_document_generator_with_llm()
        test_full_integration_with_llm()
        
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
