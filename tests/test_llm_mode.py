"""
Change Analyzer + Document Generator LLM 모드 테스트

실제 OpenAI API를 사용하여 LLM 기반 분석 및 문서 생성을 테스트합니다.
"""

import os
import json
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# 테스트 대상 모듈들
import sys
sys.path.append('.')
from domain.langgraph.nodes.change_analyzer_node import change_analyzer_node
from domain.langgraph.nodes.document_generator_node import document_generator_node
from domain.langgraph.document_state import DocumentState
from langchain_openai import ChatOpenAI

class TestLLMMode:
    """LLM 모드 테스트"""
    
    def __init__(self):
        self.test_results_dir = Path("test_results")
        self.test_results_dir.mkdir(exist_ok=True)
        self.test_session = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # .env 파일 로드
        from dotenv import load_dotenv
        load_dotenv()
        
        # API 키 확인
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
        
        # LLM 초기화
        self.llm = ChatOpenAI(
            api_key=lambda: self.api_key,
            model="gpt-4o-mini",  # 비용 절약을 위해 mini 사용
            temperature=0.1
        )
        print(f"✅ LLM initialized with model: gpt-4o-mini")
        
    def save_test_result(self, test_name: str, result: Dict[str, Any]):
        """테스트 결과를 파일로 저장"""
        result_file = self.test_results_dir / f"{self.test_session}_llm_{test_name}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"✅ Test result saved: {result_file}")

    def create_realistic_state(self, scenario: str) -> DocumentState:
        """실제적인 테스트 시나리오 생성"""
        base_state: DocumentState = {
            "code_change_id": 1,
            "status": "analyzing",
            "should_update": False,
        }
        
        if scenario == "feature_auth":
            base_state.update({
                "changed_files": [
                    "src/auth/authentication.py", 
                    "src/auth/jwt_handler.py",
                    "src/models/user.py",
                    "tests/test_auth.py"
                ],
                "code_change": {
                    "commit_sha": "a1b2c3d4",
                    "commit_message": "feat: implement JWT-based user authentication system",
                    "diff_content": """
+class JWTHandler:
+    def __init__(self, secret_key: str, algorithm: str = "HS256"):
+        self.secret_key = secret_key
+        self.algorithm = algorithm
+    
+    def encode_token(self, payload: dict) -> str:
+        \"\"\"JWT 토큰을 생성합니다.\"\"\"
+        payload['exp'] = datetime.utcnow() + timedelta(hours=24)
+        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
+    
+    def decode_token(self, token: str) -> dict:
+        \"\"\"JWT 토큰을 검증하고 디코딩합니다.\"\"\"
+        try:
+            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
+            return payload
+        except jwt.ExpiredSignatureError:
+            raise HTTPException(status_code=401, detail="Token has expired")
+        except jwt.InvalidTokenError:
+            raise HTTPException(status_code=401, detail="Invalid token")

+def authenticate_user(credentials: UserCredentials) -> AuthResponse:
+    \"\"\"사용자 인증을 수행합니다.\"\"\"
+    user = get_user_by_email(credentials.email)
+    if not user or not verify_password(credentials.password, user.hashed_password):
+        raise HTTPException(status_code=401, detail="Invalid credentials")
+    
+    access_token = jwt_handler.encode_token({"sub": user.id, "email": user.email})
+    return AuthResponse(access_token=access_token, token_type="bearer")
                    """
                }
            })
        elif scenario == "bugfix_database":
            base_state.update({
                "changed_files": [
                    "src/database/connection.py",
                    "src/utils/retry.py"
                ],
                "code_change": {
                    "commit_sha": "e5f6g7h8",
                    "commit_message": "fix: resolve database connection pool exhaustion issue",
                    "diff_content": """
-DATABASE_URL = "postgresql://user:pass@localhost/db"
-engine = create_engine(DATABASE_URL)
+DATABASE_URL = "postgresql://user:pass@localhost/db"
+engine = create_engine(
+    DATABASE_URL,
+    pool_size=20,
+    max_overflow=30,
+    pool_pre_ping=True,
+    pool_recycle=3600
+)

+@retry(max_attempts=3, delay=1.0)
+def get_database_connection():
+    \"\"\"데이터베이스 연결을 안전하게 가져옵니다.\"\"\"
+    try:
+        connection = engine.connect()
+        # 연결 테스트
+        connection.execute(text("SELECT 1"))
+        return connection
+    except SQLAlchemyError as e:
+        logger.error(f"Database connection failed: {e}")
+        raise
                    """
                }
            })
        elif scenario == "refactor_api":
            base_state.update({
                "changed_files": [
                    "src/api/v1/users.py",
                    "src/api/v1/orders.py", 
                    "src/schemas/response.py",
                    "src/middleware/validation.py"
                ],
                "code_change": {
                    "commit_sha": "i9j0k1l2",
                    "commit_message": "refactor: standardize API response format and add request validation",
                    "diff_content": """
+class APIResponse(BaseModel):
+    \"\"\"표준 API 응답 형식\"\"\"
+    success: bool
+    data: Optional[Any] = None
+    message: str = ""
+    errors: Optional[List[str]] = None
+    timestamp: datetime = Field(default_factory=datetime.utcnow)

-@app.get("/users/{user_id}")
-def get_user(user_id: int):
-    user = db.query(User).filter(User.id == user_id).first()
-    if not user:
-        return {"error": "User not found"}
-    return {"user": user}
+@app.get("/users/{user_id}", response_model=APIResponse)
+def get_user(user_id: int = Path(..., gt=0)):
+    try:
+        user = db.query(User).filter(User.id == user_id).first()
+        if not user:
+            return APIResponse(success=False, message="User not found")
+        return APIResponse(success=True, data=user, message="User retrieved successfully")
+    except Exception as e:
+        return APIResponse(success=False, message="Internal server error", errors=[str(e)])
                    """
                }
            })
        elif scenario == "document_update":
            base_state.update({
                "should_update": True,
                "changed_files": ["README.md", "docs/deployment.md"],
                "existing_document": {
                    "id": 1,
                    "title": "FastAPI Authentication Service Documentation",
                    "content": """# FastAPI Authentication Service Documentation

## Overview
This service provides JWT-based authentication for web applications.

## Features
- User registration and login
- JWT token generation and validation
- Password hashing with bcrypt
- Rate limiting for security

## API Endpoints
- POST /auth/register - User registration
- POST /auth/login - User authentication
- GET /auth/me - Get current user info

## Recent Changes
- Initial authentication system implementation
                    """
                },
                "code_change": {
                    "commit_sha": "m3n4o5p6",
                    "commit_message": "docs: add deployment guide and update API documentation",
                    "diff_content": """
+## Deployment
+
+### Prerequisites
+- Python 3.9+
+- PostgreSQL 12+
+- Redis 6+ (for session management)
+
+### Environment Variables
+```env
+SECRET_KEY=your-secret-key
+DATABASE_URL=postgresql://user:pass@localhost/db
+REDIS_URL=redis://localhost:6379/0
+```
+
+### Docker Deployment
+```bash
+docker-compose up -d
+```

+## New API Endpoints (v2)
+- POST /auth/refresh - Refresh access token
+- POST /auth/logout - User logout
+- PATCH /auth/password - Change password
                    """
                }
            })
            
        return base_state

    async def test_change_analyzer_llm(self):
        """Change Analyzer LLM 모드 테스트"""
        print("\n🧪 Testing Change Analyzer (LLM Mode)")
        
        scenarios = ["feature_auth", "bugfix_database", "refactor_api"]
        results = {}
        
        for scenario in scenarios:
            print(f"  📋 Testing scenario: {scenario}")
            
            # State 생성
            state = self.create_realistic_state(scenario)
            
            # Change Analyzer 실행 (LLM 모드)
            try:
                result_state = change_analyzer_node(state, llm=self.llm, use_mock=False)
                
                # 결과 검증
                analysis_result = result_state.get("analysis_result", "")
                
                results[scenario] = {
                    "success": True,
                    "input": {
                        "changed_files": state.get("changed_files", []),
                        "commit_message": state.get("code_change", {}).get("commit_message", ""),
                        "diff_lines": len(state.get("code_change", {}).get("diff_content", "").split('\n'))
                    },
                    "output": {
                        "status": result_state.get("status"),
                        "analysis_length": len(analysis_result),
                        "analysis_content": analysis_result,
                        "has_korean": "한국어" in analysis_result or any(ord(c) > 127 for c in analysis_result),
                        "contains_technical_terms": any(term in analysis_result.lower() for term in ["jwt", "database", "api", "authentication", "connection"])
                    }
                }
                
                print(f"    ✅ Analysis completed: {len(analysis_result)} chars")
                
            except Exception as e:
                results[scenario] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__
                }
                print(f"    ❌ Analysis failed: {e}")
        
        # 결과 저장
        self.save_test_result("change_analyzer", results)

    async def test_document_generator_llm(self):
        """Document Generator LLM 모드 테스트"""
        print("\n🧪 Testing Document Generator (LLM Mode)")
        
        scenarios = ["feature_auth", "bugfix_database", "refactor_api"]
        results = {}
        
        for scenario in scenarios:
            print(f"  📋 Testing scenario: {scenario}")
            
            # State 생성 및 분석 결과 추가
            state = self.create_realistic_state(scenario)
            
            # 먼저 분석 수행
            analyzed_state = change_analyzer_node(state, llm=self.llm, use_mock=False)
            
            try:
                # Document Generator 실행 (LLM 모드)
                final_state = document_generator_node(analyzed_state, llm=self.llm, use_mock=False)
                
                document_content = final_state.get("document_content", "")
                document_summary = final_state.get("document_summary", "")
                
                results[scenario] = {
                    "success": True,
                    "input": {
                        "analysis_result": analyzed_state.get("analysis_result", ""),
                        "changed_files": state.get("changed_files", []),
                        "scenario_type": scenario
                    },
                    "output": {
                        "status": final_state.get("status"),
                        "document_length": len(document_content),
                        "summary_length": len(document_summary),
                        "document_content": document_content,
                        "document_summary": document_summary,
                        "has_markdown": "##" in document_content or "#" in document_content,
                        "has_code_blocks": "```" in document_content,
                        "structure_analysis": {
                            "has_headers": document_content.count("#") > 0,
                            "has_lists": document_content.count("-") > 3,
                            "paragraph_count": document_content.count("\n\n")
                        }
                    }
                }
                
                print(f"    ✅ Document generated: {len(document_content)} chars, Summary: {len(document_summary)} chars")
                
            except Exception as e:
                results[scenario] = {
                    "success": False,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "analysis_result": analyzed_state.get("analysis_result", "")
                }
                print(f"    ❌ Document generation failed: {e}")
        
        # 결과 저장
        self.save_test_result("document_generator", results)

    async def test_document_update_llm(self):
        """문서 업데이트 LLM 모드 테스트"""
        print("\n🧪 Testing Document Update (LLM Mode)")
        
        # 문서 업데이트 시나리오
        state = self.create_realistic_state("document_update")
        
        try:
            print("  📋 Step 1: Change Analysis")
            # 1. 변경사항 분석
            analyzed_state = change_analyzer_node(state, llm=self.llm, use_mock=False)
            
            print("  📋 Step 2: Document Update")
            # 2. 문서 업데이트
            final_state = document_generator_node(analyzed_state, llm=self.llm, use_mock=False)
            
            # 결과 분석
            original_content = state.get("existing_document", {}).get("content", "")
            updated_content = final_state.get("document_content", "")
            
            result = {
                "success": True,
                "workflow": "document_update_llm",
                "steps": {
                    "1_analysis": {
                        "status": analyzed_state.get("status"),
                        "analysis_length": len(analyzed_state.get("analysis_result", "")),
                        "analysis_content": analyzed_state.get("analysis_result", "")
                    },
                    "2_document_update": {
                        "status": final_state.get("status"),
                        "original_length": len(original_content),
                        "updated_length": len(updated_content),
                        "content_changed": original_content != updated_content,
                        "summary": final_state.get("document_summary", ""),
                        "updated_content": updated_content
                    }
                },
                "quality_analysis": {
                    "content_coherence": "Recent Changes" in updated_content,
                    "preserves_structure": "## Overview" in updated_content,
                    "adds_new_information": len(updated_content) > len(original_content),
                    "maintains_formatting": updated_content.count("#") >= original_content.count("#"),
                    "integration_quality": {
                        "smooth_integration": "deployment" in updated_content.lower() or "환경변수" in updated_content,
                        "proper_sectioning": updated_content.count("##") > original_content.count("##"),
                        "maintains_context": "authentication" in updated_content.lower()
                    }
                }
            }
            
            print(f"    ✅ Document updated: {len(original_content)} → {len(updated_content)} chars")
            
        except Exception as e:
            result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            print(f"    ❌ Document update failed: {e}")
        
        # 결과 저장
        self.save_test_result("document_update", result)

    async def test_quality_comparison(self):
        """Mock vs LLM 품질 비교 테스트"""
        print("\n🧪 Testing Quality Comparison (Mock vs LLM)")
        
        scenario = "feature_auth"
        state = self.create_realistic_state(scenario)
        
        results = {}
        
        try:
            # Mock 모드 테스트
            print("  📋 Testing Mock Mode")
            mock_analyzed = change_analyzer_node(state, llm=None, use_mock=True)
            mock_document = document_generator_node(mock_analyzed, llm=None, use_mock=True)
            
            # LLM 모드 테스트
            print("  📋 Testing LLM Mode")
            llm_analyzed = change_analyzer_node(state, llm=self.llm, use_mock=False)
            llm_document = document_generator_node(llm_analyzed, llm=self.llm, use_mock=False)
            
            # 품질 비교
            results = {
                "scenario": scenario,
                "mock_results": {
                    "analysis_length": len(mock_analyzed.get("analysis_result", "")),
                    "document_length": len(mock_document.get("document_content", "")),
                    "analysis_content": mock_analyzed.get("analysis_result", ""),
                    "document_content": mock_document.get("document_content", "")
                },
                "llm_results": {
                    "analysis_length": len(llm_analyzed.get("analysis_result", "")),
                    "document_length": len(llm_document.get("document_content", "")),
                    "analysis_content": llm_analyzed.get("analysis_result", ""),
                    "document_content": llm_document.get("document_content", "")
                },
                "quality_comparison": {
                    "analysis_detail_ratio": len(llm_analyzed.get("analysis_result", "")) / max(len(mock_analyzed.get("analysis_result", "")), 1),
                    "document_detail_ratio": len(llm_document.get("document_content", "")) / max(len(mock_document.get("document_content", "")), 1),
                    "llm_has_technical_depth": "JWT" in llm_analyzed.get("analysis_result", "") and "authentication" in llm_analyzed.get("analysis_result", ""),
                    "llm_document_structure": llm_document.get("document_content", "").count("##") > mock_document.get("document_content", "").count("##"),
                    "summary_quality": {
                        "mock_summary": mock_document.get("document_summary", ""),
                        "llm_summary": llm_document.get("document_summary", ""),
                        "llm_more_descriptive": len(llm_document.get("document_summary", "")) > len(mock_document.get("document_summary", ""))
                    }
                }
            }
            
            print(f"    ✅ Comparison completed")
            print(f"        Mock Analysis: {len(mock_analyzed.get('analysis_result', ''))} chars")
            print(f"        LLM Analysis: {len(llm_analyzed.get('analysis_result', ''))} chars") 
            print(f"        Mock Document: {len(mock_document.get('document_content', ''))} chars")
            print(f"        LLM Document: {len(llm_document.get('document_content', ''))} chars")
            
        except Exception as e:
            results = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
            print(f"    ❌ Quality comparison failed: {e}")
        
        # 결과 저장
        self.save_test_result("quality_comparison", results)

async def run_llm_tests():
    """모든 LLM 테스트 실행"""
    print("🚀 Starting LLM Mode Integration Tests")
    print("=" * 70)
    
    try:
        tester = TestLLMMode()
        
        # 각 테스트 실행
        await tester.test_change_analyzer_llm()
        await tester.test_document_generator_llm()
        await tester.test_document_update_llm()
        await tester.test_quality_comparison()
        
        print("\n" + "=" * 70)
        print("🎉 All LLM tests completed! Check test_results/ directory for detailed reports.")
        print(f"📁 Results saved with session ID: {tester.test_session}")
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("💡 Please set OPENAI_API_KEY environment variable")
    except Exception as e:
        print(f"❌ Test execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_llm_tests())