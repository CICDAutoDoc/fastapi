"""
섹션 증분 업데이트(Incremental Update) 테스트

변경 부분만 생성하고 기존 섹션과 병합하는 새로운 방식을 테스트합니다.
"""

import sys
sys.path.append('.')

from domain.langgraph.nodes.document_generator_node import (
    _merge_changelog,
    _merge_section_changes,
    _handle_partial_update
)
from domain.langgraph.document_state import DocumentState


def test_merge_changelog():
    """Changelog 병합 테스트"""
    print("\n🧪 Test 1: Changelog Merge")
    print("=" * 70)
    
    # 테스트 케이스 1: 기존 changelog에 새 항목 추가
    old_changelog = """- 2024-01-01: Initial version
- 2024-01-15: Added user authentication"""
    
    new_entry = "- 2024-02-01: Implemented payment system"
    
    result = _merge_changelog(old_changelog, new_entry)
    
    print("📝 Old Changelog:")
    print(old_changelog)
    print("\n➕ New Entry:")
    print(new_entry)
    print("\n✅ Merged Result:")
    print(result)
    
    assert "Initial version" in result
    assert "user authentication" in result
    assert "payment system" in result
    assert result.count("2024-") == 3
    
    # 테스트 케이스 2: 빈 changelog
    print("\n" + "-" * 70)
    print("Test Case 2: Empty Changelog")
    
    result2 = _merge_changelog("", new_entry)
    print(f"Result: {result2}")
    assert result2 == new_entry
    
    # 테스트 케이스 3: NO_CHANGE
    print("\n" + "-" * 70)
    print("Test Case 3: No Change")
    
    result3 = _merge_changelog(old_changelog, "[NO_CHANGE]")
    print(f"Result: {result3 == old_changelog}")
    assert result3 == old_changelog
    
    print("\n✅ All changelog merge tests passed!")


def test_merge_section_changes_add():
    """[ADD] 마커 병합 테스트"""
    print("\n\n🧪 Test 2: Section Changes - ADD Marker")
    print("=" * 70)
    
    old_section = """## Modules

### User Module
Handles user registration and authentication.

### Product Module
Manages product catalog."""
    
    # [ADD] 마커로 새 모듈 추가
    changes = """[ADD]

### Payment Module
Processes payments using Stripe integration."""
    
    result = _merge_section_changes(old_section, changes)
    
    print("📝 Old Section:")
    print(old_section)
    print("\n➕ Changes (with [ADD]):")
    print(changes)
    print("\n✅ Merged Result:")
    print(result)
    
    assert "User Module" in result
    assert "Product Module" in result
    assert "Payment Module" in result
    assert "Stripe integration" in result
    
    print("\n✅ ADD marker test passed!")


def test_merge_section_changes_update():
    """[UPDATE] 마커 병합 테스트"""
    print("\n\n🧪 Test 3: Section Changes - UPDATE Marker")
    print("=" * 70)
    
    old_section = """## Architecture

The application uses a monolithic architecture with the following layers:
- Presentation Layer: FastAPI endpoints
- Business Logic: Service classes
- Data Access: SQLAlchemy ORM

Currently deployed on a single server."""
    
    # [UPDATE] 마커로 특정 부분 수정
    changes = """[UPDATE: Currently deployed on a single server]

Now deployed on Kubernetes cluster with auto-scaling capabilities."""
    
    result = _merge_section_changes(old_section, changes)
    
    print("📝 Old Section:")
    print(old_section)
    print("\n🔄 Changes (with [UPDATE]):")
    print(changes)
    print("\n✅ Merged Result:")
    print(result)
    
    assert "monolithic architecture" in result
    assert "FastAPI endpoints" in result
    assert "Kubernetes cluster" in result
    assert "single server" not in result or "Now deployed" in result
    
    print("\n✅ UPDATE marker test passed!")


def test_merge_section_changes_no_change():
    """[NO_CHANGE] 처리 테스트"""
    print("\n\n🧪 Test 4: Section Changes - NO_CHANGE")
    print("=" * 70)
    
    old_section = """## Overview

This is a FastAPI application for managing user data."""
    
    changes = "[NO_CHANGE]"
    
    result = _merge_section_changes(old_section, changes)
    
    print("📝 Old Section:")
    print(old_section)
    print("\n⏸️  Changes:")
    print(changes)
    print("\n✅ Result (should be unchanged):")
    print(result)
    
    assert result == old_section
    
    print("\n✅ NO_CHANGE test passed!")


def test_merge_section_changes_mixed():
    """혼합 마커 테스트 (ADD + UPDATE)"""
    print("\n\n🧪 Test 5: Mixed Changes (ADD + UPDATE)")
    print("=" * 70)
    
    old_section = """## Features

- User authentication
- Product management
- Basic reporting"""
    
    # ADD와 UPDATE 혼합
    changes = """[UPDATE: Basic reporting]

- Advanced analytics dashboard with real-time metrics

[ADD]

- Payment processing with Stripe
- Email notification system"""
    
    result = _merge_section_changes(old_section, changes)
    
    print("📝 Old Section:")
    print(old_section)
    print("\n🔄 Mixed Changes:")
    print(changes)
    print("\n✅ Merged Result:")
    print(result)
    
    assert "User authentication" in result
    assert "Product management" in result
    assert "analytics dashboard" in result
    assert "Payment processing" in result
    assert "Email notification" in result
    
    print("\n✅ Mixed changes test passed!")


def test_partial_update_with_mock():
    """전체 부분 업데이트 플로우 테스트 (Mock 모드)"""
    print("\n\n🧪 Test 6: Full Partial Update Flow (Mock Mode)")
    print("=" * 70)
    
    state: DocumentState = {
        "code_change_id": 1,
        "status": "generating",
        "should_update": True,
        "existing_document": {
            "title": "API Documentation",
            "content": """# API Documentation

## Overview
FastAPI application for user management.

## Modules

### User Module
Handles user operations.

## Changelog
- 2024-01-01: Initial version
"""
        },
        "file_change_summaries": [
            {
                "file": "src/api/payment_router.py",
                "priority": "high",
                "change_type": "added",
                "summary": "Added new payment endpoint"
            }
        ],
        "analysis_result": "Added payment processing functionality",
        "changed_files": ["src/api/payment_router.py"],
        "code_change": {
            "commit_sha": "abc123",
            "commit_message": "feat: Add payment processing"
        },
        "target_doc_sections": ["modules", "changelog"]
    }
    
    print("📋 Testing partial update with mock mode...")
    print(f"  Target sections: {state['target_doc_sections']}")
    print(f"  Changed files: {state['changed_files']}")
    
    # Mock 모드로 부분 업데이트 실행
    result_state = _handle_partial_update(state, llm=None, use_mock=True)
    
    print("\n✅ Update complete!")
    print(f"  Status: {result_state['status']}")
    print(f"  Updated sections: {len(result_state.get('updated_sections', []))}")
    
    if "document_content" in result_state:
        print("\n📄 Updated Document:")
        print("-" * 70)
        print(result_state["document_content"])
        print("-" * 70)
    
    # 검증
    assert result_state["status"] == "saving"
    assert "document_content" in result_state
    assert "updated_sections" in result_state
    
    content = result_state["document_content"]
    assert "Overview" in content  # 기존 섹션 보존
    assert "User Module" in content  # 기존 내용 보존
    assert "feat: Add payment processing" in content  # 새 changelog 추가
    
    print("\n✅ Full partial update test passed!")


def test_section_preservation():
    """섹션 보존 테스트 - 변경되지 않은 섹션은 그대로 유지"""
    print("\n\n🧪 Test 7: Section Preservation")
    print("=" * 70)
    
    old_section = """## Architecture

### Layer 1: API Layer
FastAPI endpoints handle HTTP requests.

### Layer 2: Business Logic
Service classes implement business rules.

### Layer 3: Data Access
SQLAlchemy models and repositories."""
    
    # 일부만 변경 (Layer 2만 수정)
    changes = """[UPDATE: Service classes implement business rules]

Service classes implement business rules with improved error handling and logging."""
    
    result = _merge_section_changes(old_section, changes)
    
    print("📝 Old Section:")
    print(old_section)
    print("\n🔄 Changes (only Layer 2):")
    print(changes)
    print("\n✅ Merged Result:")
    print(result)
    
    # Layer 1과 Layer 3는 그대로 유지되어야 함
    assert "Layer 1: API Layer" in result
    assert "FastAPI endpoints handle HTTP requests" in result
    assert "Layer 3: Data Access" in result
    assert "SQLAlchemy models" in result
    
    # Layer 2만 변경
    assert "improved error handling" in result
    
    print("\n✅ Section preservation test passed!")


if __name__ == "__main__":
    print("\n🚀 Starting Incremental Section Update Tests")
    print("=" * 70)
    
    try:
        test_merge_changelog()
        test_merge_section_changes_add()
        test_merge_section_changes_update()
        test_merge_section_changes_no_change()
        test_merge_section_changes_mixed()
        test_partial_update_with_mock()
        test_section_preservation()
        
        print("\n" + "=" * 70)
        print("🎉 All incremental update tests passed successfully!")
        print("\n✅ Summary:")
        print("  - Changelog merge: ✓")
        print("  - [ADD] marker: ✓")
        print("  - [UPDATE] marker: ✓")
        print("  - [NO_CHANGE]: ✓")
        print("  - Mixed changes: ✓")
        print("  - Full flow: ✓")
        print("  - Section preservation: ✓")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
        import traceback
        traceback.print_exc()
