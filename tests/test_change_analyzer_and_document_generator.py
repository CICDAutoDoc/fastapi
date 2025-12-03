"""
Change Analyzer + Document Generator 통합 테스트

이 테스트는 변경사항 분석부터 문서 업데이트까지의 전체 과정을 검증합니다.
"""

import pytest
import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# 테스트 대상 모듈들 (상대 경로)
import sys
sys.path.append('.')
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from domain.langgraph.document_state import DocumentState

class TestChangeAnalysisAndDocumentGeneration:
    """변경사항 분석과 문서 생성 통합 테스트"""
    
    def __init__(self):
        self.test_results_dir = Path("test_results")
        self.test_results_dir.mkdir(exist_ok=True)
        self.test_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        
    def create_mock_state(self, scenario: str) -> DocumentState:
        """테스트 시나리오별 Mock State 생성"""
        base_state: DocumentState = {
            "code_change_id": 1,
            "status": "analyzing",
            "should_update": False,
        }
        
        if scenario == "new_feature":
            base_state.update({
                "changed_files": ["src/api/new_endpoint.py", "src/models/user.py"],
                "code_change": {
                    "commit_sha": "abc1234",
                    "commit_message": "Add new user authentication endpoint",
                    "diff_content": """
+def authenticate_user(username: str, password: str) -> dict:
+    \"\"\"새로운 사용자 인증 함수\"\"\"
+    if verify_credentials(username, password):
+        return {"token": generate_jwt(username)}
+    raise AuthenticationError("Invalid credentials")
                    """
                }
            })
        elif scenario == "bug_fix":
            base_state.update({
                "changed_files": ["src/utils/validator.py"],
                "code_change": {
                    "commit_sha": "def5678",
                    "commit_message": "Fix email validation regex bug",
                    "diff_content": """
-EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
+EMAIL_REGEX = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
                    """
                }
            })
        elif scenario == "refactoring":
            base_state.update({
                "changed_files": ["src/services/payment.py", "src/models/order.py", "tests/test_payment.py"],
                "code_change": {
                    "commit_sha": "ghi9012",
                    "commit_message": "Refactor payment service to use new architecture",
                    "diff_content": """
-class PaymentService:
-    def process_payment(self, amount, method):
-        # Old implementation
+class PaymentProcessor:
+    def process_payment(self, payment_request: PaymentRequest) -> PaymentResult:
+        # New architecture with better type safety
                    """
                }
            })
        elif scenario == "document_update":
            base_state.update({
                "should_update": True,
                "changed_files": ["README.md", "docs/api.md"],
                "existing_document": {
                    "id": 1,
                    "title": "Project Documentation",
                    "content": """# Project Documentation

## Overview
This is an existing project documentation.

## Features
- Feature A
- Feature B

## Recent Changes
- Initial version created
                    """
                },
                "code_change": {
                    "commit_sha": "jkl3456",
                    "commit_message": "Update documentation with new API endpoints",
                    "diff_content": """
+## New Endpoints
+- POST /api/auth/login
+- GET /api/users/profile
                    """
                }
            })
            
        return base_state
    
    def save_test_result(self, test_name: str, result: Dict[str, Any]):
        """테스트 결과를 파일로 저장"""
        result_file = self.test_results_dir / f"{self.test_session}_{test_name}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ Test result saved: {result_file}")

    @pytest.mark.asyncio
    async def test_change_analyzer_mock_mode(self):
        """Change Analyzer Mock 모드 테스트"""
        print("\n🧪 Testing Change Analyzer (Mock Mode)")
        
        scenarios = ["new_feature", "bug_fix", "refactoring"]
        results = {}
        
        for scenario in scenarios:
            print(f"  📋 Testing scenario: {scenario}")
            
            # Mock State 생성
            state = self.create_mock_state(scenario)
            
            # Change Analyzer 실행 (Mock 모드)
            result_state = change_analyzer_node(state, llm=None, use_mock=True)
            
            # 결과 검증
            assert result_state["status"] == "generating"
            assert "analysis_result" in result_state
            assert len(result_state["analysis_result"]) > 0
            
            results[scenario] = {
                "input": {
                    "changed_files": state.get("changed_files", []),
                    "commit_message": state.get("code_change", {}).get("commit_message", ""),
                    "diff_content": len(state.get("code_change", {}).get("diff_content", ""))
                },
                "output": {
                    "status": result_state["status"],
                    "analysis_length": len(result_state["analysis_result"]),
                    "analysis_preview": result_state["analysis_result"][:200] + "..."
                }
            }
            
            print(f"    ✅ Analysis generated: {len(result_state['analysis_result'])} chars")
        
        # 결과 저장
        self.save_test_result("change_analyzer_mock", results)
        
    @pytest.mark.asyncio
    async def test_document_generator_mock_mode(self):
        """Document Generator Mock 모드 테스트"""
        print("\n🧪 Testing Document Generator (Mock Mode)")
        
        scenarios = ["new_feature", "bug_fix", "refactoring"]
        results = {}
        
        for scenario in scenarios:
            print(f"  📋 Testing scenario: {scenario}")
            
            # Mock State 생성 및 분석 결과 추가
            state = self.create_mock_state(scenario)
            state["analysis_result"] = f"Mock analysis for {scenario}: This change introduces significant improvements to the codebase architecture."
            
            # Document Generator 실행 (Mock 모드)
            result_state = document_generator_node(state, llm=None, use_mock=True)
            
            # 결과 검증
            assert result_state["status"] == "saving"
            assert "document_content" in result_state
            assert "document_summary" in result_state
            assert len(result_state["document_content"]) > 0
            
            results[scenario] = {
                "input": {
                    "analysis_result": state["analysis_result"],
                    "changed_files": state.get("changed_files", []),
                    "commit_sha": state.get("code_change", {}).get("commit_sha", "")
                },
                "output": {
                    "status": result_state["status"],
                    "document_length": len(result_state["document_content"]),
                    "document_preview": result_state["document_content"][:300] + "...",
                    "summary": result_state["document_summary"]
                }
            }
            
            print(f"    ✅ Document generated: {len(result_state['document_content'])} chars")
        
        # 결과 저장
        self.save_test_result("document_generator_mock", results)

    @pytest.mark.asyncio
    async def test_document_update_workflow(self):
        """문서 업데이트 워크플로우 테스트"""
        print("\n🧪 Testing Document Update Workflow")
        
        # 기존 문서 업데이트 시나리오
        state = self.create_mock_state("document_update")
        
        print("  📋 Step 1: Change Analysis")
        # 1. 변경사항 분석
        analyzed_state = change_analyzer_node(state, llm=None, use_mock=True)
        assert analyzed_state["status"] == "generating"
        assert "analysis_result" in analyzed_state
        
        print("  📋 Step 2: Document Generation (Update)")
        # 2. 문서 업데이트
        final_state = document_generator_node(analyzed_state, llm=None, use_mock=True)
        assert final_state["status"] == "saving"
        assert "document_content" in final_state
        
        # 결과 분석
        original_content = state["existing_document"]["content"]
        updated_content = final_state["document_content"]
        
        result = {
            "workflow": "document_update",
            "steps": {
                "1_analysis": {
                    "status": analyzed_state["status"],
                    "analysis_length": len(analyzed_state["analysis_result"]),
                    "analysis_preview": analyzed_state["analysis_result"][:200] + "..."
                },
                "2_document_update": {
                    "status": final_state["status"],
                    "original_length": len(original_content),
                    "updated_length": len(updated_content),
                    "content_changed": original_content != updated_content,
                    "summary": final_state["document_summary"]
                }
            },
            "validation": {
                "should_update_flag": state["should_update"],
                "existing_document_processed": "existing_document" in state,
                "content_preservation": "# Project Documentation" in updated_content,
                "new_content_added": len(updated_content) >= len(original_content)
            }
        }
        
        # 결과 저장
        self.save_test_result("document_update_workflow", result)
        print(f"    ✅ Workflow completed: {original_content != updated_content}")

    @pytest.mark.asyncio 
    async def test_integration_with_different_commit_types(self):
        """다양한 커밋 타입별 통합 테스트"""
        print("\n🧪 Testing Integration with Different Commit Types")
        
        # 다양한 커밋 타입 시나리오
        commit_scenarios = {
            "feat": {
                "message": "feat: add user profile management",
                "files": ["src/controllers/profile.py", "src/models/profile.py"],
                "expected_keywords": ["기능", "추가", "profile"]
            },
            "fix": {
                "message": "fix: resolve database connection timeout",
                "files": ["src/database/connection.py"],
                "expected_keywords": ["수정", "버그", "database"]
            },
            "docs": {
                "message": "docs: update API documentation",
                "files": ["docs/api.md", "README.md"],
                "expected_keywords": ["문서", "업데이트", "API"]
            },
            "refactor": {
                "message": "refactor: improve error handling structure",
                "files": ["src/utils/errors.py", "src/handlers/error_handler.py"],
                "expected_keywords": ["리팩터링", "구조", "error"]
            }
        }
        
        results = {}
        
        for commit_type, scenario in commit_scenarios.items():
            print(f"  📋 Testing commit type: {commit_type}")
            
            # State 생성
            state = self.create_mock_state("new_feature")  # base template
            state["changed_files"] = scenario["files"]
            state["code_change"]["commit_message"] = scenario["message"]
            
            # 전체 파이프라인 실행
            # 1. 분석
            analyzed_state = change_analyzer_node(state, llm=None, use_mock=True)
            
            # 2. 문서 생성  
            final_state = document_generator_node(analyzed_state, llm=None, use_mock=True)
            
            # 키워드 검증
            content_lower = final_state["document_content"].lower()
            keywords_found = [kw for kw in scenario["expected_keywords"] 
                            if kw.lower() in content_lower]
            
            results[commit_type] = {
                "scenario": scenario,
                "analysis_status": analyzed_state["status"],
                "document_status": final_state["status"],
                "keywords_found": keywords_found,
                "keywords_coverage": len(keywords_found) / len(scenario["expected_keywords"]),
                "document_length": len(final_state["document_content"]),
                "summary": final_state["document_summary"]
            }
            
            print(f"    ✅ Keywords found: {keywords_found}")
        
        # 결과 저장
        self.save_test_result("integration_commit_types", results)

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """에러 처리 테스트"""
        print("\n🧪 Testing Error Handling")
        
        error_scenarios = {
            "missing_commit_info": {
                "state": {"code_change_id": 1, "status": "analyzing"},
                "expected_error": True
            },
            "empty_changed_files": {
                "state": {
                    "code_change_id": 1,
                    "status": "analyzing", 
                    "changed_files": [],
                    "code_change": {"commit_sha": "abc123", "commit_message": "test"}
                },
                "expected_error": False  # 빈 파일 리스트는 허용될 수 있음
            },
            "missing_diff_content": {
                "state": {
                    "code_change_id": 1,
                    "status": "analyzing",
                    "changed_files": ["test.py"],
                    "code_change": {"commit_sha": "abc123", "commit_message": "test"}
                },
                "expected_error": False  # diff 없어도 처리 가능해야 함
            }
        }
        
        results = {}
        
        for scenario_name, scenario in error_scenarios.items():
            print(f"  📋 Testing error scenario: {scenario_name}")
            
            try:
                # Change Analyzer 실행
                state = scenario["state"]
                result_state = change_analyzer_node(state, llm=None, use_mock=True)
                
                results[scenario_name] = {
                    "error_occurred": False,
                    "final_status": result_state.get("status", "unknown"),
                    "has_error_field": "error" in result_state,
                    "error_message": result_state.get("error", None)
                }
                
                print(f"    ✅ Handled gracefully: {result_state.get('status', 'unknown')}")
                
            except Exception as e:
                results[scenario_name] = {
                    "error_occurred": True,
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                }
                
                if scenario["expected_error"]:
                    print(f"    ✅ Expected error caught: {type(e).__name__}")
                else:
                    print(f"    ❌ Unexpected error: {e}")
        
        # 결과 저장
        self.save_test_result("error_handling", results)

def run_all_tests():
    """모든 테스트 실행"""
    print("🚀 Starting Change Analyzer + Document Generator Integration Tests")
    print("=" * 70)
    
    tester = TestChangeAnalysisAndDocumentGeneration()
    
    # 각 테스트 실행
    import asyncio
    
    async def run_tests():
        await tester.test_change_analyzer_mock_mode()
        await tester.test_document_generator_mock_mode()  
        await tester.test_document_update_workflow()
        await tester.test_integration_with_different_commit_types()
        await tester.test_error_handling()
    
    asyncio.run(run_tests())
    
    print("\n" + "=" * 70)
    print("🎉 All tests completed! Check test_results/ directory for detailed reports.")
    print(f"📁 Results saved with session ID: {tester.test_session}")

if __name__ == "__main__":
    run_all_tests()