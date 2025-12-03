"""
Test to verify that v4 prompts no longer append metadata lines like {"section":"...","version":"v4"}
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from domain.langgraph.nodes.prompts import get_prompt_set

def test_v4_prompts_no_metadata():
    """v4 프롬프트가 섹션 종료 메타데이터를 포함하지 않는지 확인"""
    
    # 샘플 데이터
    sample_files = [
        {
            "file_path": "main.py",
            "language": "python",
            "summary": {
                "purpose": "Application entry point",
                "functions_count": 3,
                "classes_count": 1,
                "role": "entry"
            }
        }
    ]
    sample_structure = {"type": "dir", "children": []}
    repo_name = "TestRepo"
    
    # v4 프롬프트 세트 가져오기
    prompt_set = get_prompt_set("v4")
    
    # 각 섹션별 프롬프트 생성
    sections_to_test = ["overview", "architecture", "modules"]
    
    for section in sections_to_test:
        system_prompt, builder = prompt_set[section]
        human_prompt = builder(sample_files, sample_structure, repo_name)
        
        # 메타데이터 라인 체크
        metadata_patterns = [
            '{"section":"' + section,
            '"version":"v4"',
            '섹션 종료 후'
        ]
        
        for pattern in metadata_patterns:
            assert pattern not in human_prompt, \
                f"❌ {section} 프롬프트에 메타데이터 패턴 '{pattern}'이 포함되어 있습니다!\n프롬프트:\n{human_prompt}"
        
        print(f"✅ {section}: 메타데이터 없음 확인")
        print(f"   프롬프트 마지막 100자: ...{human_prompt[-100:]}")
        print()

def test_other_versions_also_no_metadata():
    """v1~v3도 메타데이터가 없는지 확인 (원래부터 없어야 함)"""
    
    sample_files = [{"file_path": "test.py", "language": "python", "summary": {}}]
    sample_structure = {}
    repo_name = "Test"
    
    for version in ["v1", "v2", "v3"]:
        prompt_set = get_prompt_set(version)
        _, builder = prompt_set["overview"]
        human_prompt = builder(sample_files, sample_structure, repo_name)
        
        assert '{"section":' not in human_prompt, \
            f"❌ {version} 프롬프트에 메타데이터가 포함되어 있습니다"
        
        print(f"✅ {version}: 메타데이터 없음 확인")

if __name__ == "__main__":
    print("="*60)
    print("프롬프트 메타데이터 제거 테스트")
    print("="*60)
    print()
    
    try:
        test_v4_prompts_no_metadata()
        print()
        test_other_versions_also_no_metadata()
        print()
        print("="*60)
        print("✅ 모든 테스트 통과: 메타데이터가 프롬프트에 포함되지 않음")
        print("="*60)
    except AssertionError as e:
        print()
        print("="*60)
        print(f"❌ 테스트 실패:\n{e}")
        print("="*60)
        sys.exit(1)
