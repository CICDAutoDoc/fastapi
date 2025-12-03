"""
전체 저장소 문서 생성 테스트
Full Repository Document Generation Test
"""

import os
import sys
import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

# 현재 프로젝트 경로를 sys.path에 추가
current_dir = Path(__file__).parent
project_root = current_dir.parent if current_dir.name == "fastapi" else current_dir
sys.path.insert(0, str(project_root))

def create_test_data() -> Dict[str, Any]:
    """테스트용 저장소 데이터 생성"""
    
    # Mock builder가 기대하는 데이터 구조에 맞게 생성
    test_files = [
        {
            "file_path": "main.py",
            "language": "python",
            "summary": {
                "purpose": "FastAPI 메인 애플리케이션 진입점",
                "functions_count": 3,
                "classes_count": 0,
                "loc": 50,
                "key_functions": ["create_app", "setup_routes", "main"]
            }
        },
        {
            "file_path": "database.py", 
            "language": "python",
            "summary": {
                "purpose": "데이터베이스 연결 및 세션 관리",
                "functions_count": 5,
                "classes_count": 1,
                "loc": 80,
                "key_functions": ["get_db", "init_db", "create_tables"]
            }
        },
        {
            "file_path": "models.py",
            "language": "python",
            "summary": {
                "purpose": "SQLAlchemy ORM 모델 정의",
                "functions_count": 2,
                "classes_count": 4,
                "loc": 120,
                "key_functions": ["create_model", "validate_data"]
            }
        },
        {
            "file_path": "app/endpoints/chat.py",
            "language": "python",
            "summary": {
                "purpose": "채팅 관련 REST API 엔드포인트",
                "functions_count": 8,
                "classes_count": 2,
                "loc": 200,
                "key_functions": ["chat_endpoint", "send_message", "get_history"]
            }
        },
        {
            "file_path": "domain/langgraph/document_workflow.py",
            "language": "python",
            "summary": {
                "purpose": "LangGraph 기반 문서 생성 워크플로우",
                "functions_count": 12,
                "classes_count": 3,
                "loc": 350,
                "key_functions": ["create_workflow", "process_document", "save_result"]
            }
        }
    ]
    
    test_structure = {
        "name": "CICDAutoDoc-FastAPI",
        "type": "directory",
        "children": [
            {"name": "main.py", "type": "file", "size": 1200},
            {"name": "database.py", "type": "file", "size": 800},
            {"name": "models.py", "type": "file", "size": 1500},
            {
                "name": "app",
                "type": "directory", 
                "children": [
                    {
                        "name": "endpoints",
                        "type": "directory",
                        "children": [
                            {"name": "chat.py", "type": "file", "size": 2000}
                        ]
                    }
                ]
            },
            {
                "name": "domain",
                "type": "directory",
                "children": [
                    {
                        "name": "langgraph",
                        "type": "directory",
                        "children": [
                            {"name": "document_workflow.py", "type": "file", "size": 5000}
                        ]
                    }
                ]
            }
        ]
    }
    
    return {
        "files": test_files,
        "structure": test_structure,
        "repo_name": "CICDAutoDoc-FastAPI"
    }

def test_with_mock():
    """Mock 데이터로 문서 생성 테스트"""
    print("🧪 Mock 데이터로 문서 생성 테스트 시작...")
    
    try:
        # 프로젝트 루트 경로를 Python path에 추가
        sys.path.insert(0, str(project_root))
        
        # Mock builder import
        from domain.langgraph.nodes.full_repository_document_generator_node import FullRepoMockBuilder
        
        # 테스트 데이터 생성
        test_data = create_test_data()
        
        # Mock builder로 문서 생성
        mock_builder = FullRepoMockBuilder(
            file_summaries=test_data["files"],
            repository_structure=test_data["structure"], 
            repository_name=test_data["repo_name"]
        )
        
        result = mock_builder.build()
        
        print("✅ Mock 문서 생성 성공!")
        print(f"제목: {result.get('title', 'N/A')}")
        print(f"요약: {result.get('summary', 'N/A')}")
        print(f"내용 길이: {len(result.get('content', ''))}")
        print(f"미리보기:\n{result.get('content', '')[:300]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ Mock 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_with_llm(api_key: str, version: str = "v4"):
    """실제 LLM으로 문서 생성 테스트"""
    print(f"🚀 LLM 버전 {version}으로 문서 생성 테스트 시작...")
    
    try:
        # 프로젝트 루트 경로를 Python path에 추가
        sys.path.insert(0, str(project_root))
        
        # LLM wrapper import
        from domain.langgraph.nodes.full_repository_document_generator_node import FullRepoDocumentLLM
        
        # 테스트 데이터 생성
        test_data = create_test_data()
        
        # LLM 초기화
        llm_generator = FullRepoDocumentLLM(api_key=api_key, prompt_version=version)
        
        print("📝 프로젝트 개요 생성 중...")
        overview = llm_generator.generate_overview(
            files=test_data["files"],
            structure=test_data["structure"],
            repo_name=test_data["repo_name"]
        )
        
        print("🏗️ 아키텍처 분석 생성 중...")
        architecture = llm_generator.generate_architecture(
            files=test_data["files"],
            structure=test_data["structure"],
            repo_name=test_data["repo_name"]
        )
        
        print("🔧 핵심 모듈 분석 생성 중...")
        modules = llm_generator.generate_key_modules(
            files=test_data["files"],
            structure=test_data["structure"],
            repo_name=test_data["repo_name"]
        )
        
        # 결과 통합
        full_document = f"""# {test_data["repo_name"]} 문서

## 프로젝트 개요
{overview}

## 아키텍처 분석
{architecture}

## 핵심 모듈
{modules}
"""
        
        result = {
            "title": f"{test_data['repo_name']} 완전 문서",
            "summary": "LLM으로 생성된 전체 저장소 문서",
            "content": full_document,
            "version": version,
            "sections": {
                "overview": overview,
                "architecture": architecture,
                "modules": modules
            }
        }
        
        print("✅ LLM 문서 생성 성공!")
        print(f"제목: {result['title']}")
        print(f"버전: {result['version']}")
        print(f"전체 내용 길이: {len(result['content'])}")
        print(f"미리보기:\n{result['content'][:500]}...")
        
        return result
        
    except Exception as e:
        print(f"❌ LLM 테스트 실패: {e}")
        import traceback  
        traceback.print_exc()
        return None

def compare_versions(api_key: str):
    """여러 프롬프트 버전 비교 테스트"""
    print("🔍 프롬프트 버전별 비교 테스트 시작...")
    
    versions = ["v1", "v2", "v3", "v4"]
    results = {}
    
    for version in versions:
        print(f"\n--- 버전 {version} 테스트 ---")
        result = test_with_llm(api_key, version)
        if result:
            results[version] = {
                "content_length": len(result["content"]),
                "title": result["title"],
                "preview": result["content"][:200] + "..."
            }
    
    print("\n📊 버전별 비교 결과:")
    for version, data in results.items():
        print(f"{version}: {data['content_length']}자, 제목: {data['title']}")
    
    return results

def save_result(result: Dict[str, Any], filename: str):
    """결과를 파일로 저장"""
    if not result:
        return
        
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    # JSON 형태로 저장
    json_file = output_dir / f"{filename}.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    
    # 마크다운 형태로 저장
    md_file = output_dir / f"{filename}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write(result.get("content", ""))
    
    print(f"💾 결과 저장됨: {json_file}, {md_file}")

def main():
    """메인 테스트 실행"""
    print("=" * 60)
    print("🚀 전체 저장소 문서 생성 테스트")
    print("=" * 60)
    
    # 1. Mock 테스트 (항상 실행)
    print("\n1️⃣ Mock 테스트")
    mock_result = test_with_mock()
    if mock_result:
        save_result(mock_result, "mock_document")
    
    # 2. LLM 테스트 (API 키가 있는 경우)
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key and api_key != "your_openai_api_key_here":
        print("\n2️⃣ LLM 테스트")
        
        # 단일 버전 테스트
        llm_result = test_with_llm(api_key)  # 기본값 v4 사용
        if llm_result:
            save_result(llm_result, "llm_document_v4")
        
        # 버전 비교 테스트 (선택적)
        compare_input = input("\n모든 버전 비교 테스트를 실행하시겠습니까? (y/N): ")
        if compare_input.lower() == 'y':
            print("\n3️⃣ 버전 비교 테스트")
            compare_results = compare_versions(api_key)
            save_result(compare_results, "version_comparison")
    else:
        print("\n⚠️ OPENAI_API_KEY가 설정되지 않아 LLM 테스트를 건너뜁니다.")
        print("API 키 설정: $env:OPENAI_API_KEY=\"your-api-key\"")
    
    print("\n✨ 테스트 완료!")

if __name__ == "__main__":
    main()