"""
File Summarizer Node LLM 테스트
LLM을 사용하여 실제 파일 요약 결과를 테스트하고 품질을 평가합니다.
"""

import sys
import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime
from dotenv import load_dotenv

# 프로젝트 루트를 Python 경로에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

# .env 파일 로드
load_dotenv()

from domain.langgraph.nodes.file_summarizer_node import file_summarizer_node
from domain.langgraph.nodes.file_parser_node import file_parser_node
from domain.langgraph.document_state import DocumentState


class FileSummarizerTester:
    """File Summarizer LLM 테스트 클래스"""
    
    def __init__(self, openai_api_key: str | None = None):
        """
        테스터 초기화
        
        Args:
            openai_api_key: OpenAI API 키. None이면 환경변수에서 가져옴
        """
        self.api_key = openai_api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            print("⚠️  OPENAI_API_KEY가 설정되지 않았습니다. Mock 모드로 실행됩니다.")
        
        self.test_results = []
        self.project_root = Path(project_root)
    
    def get_test_files(self) -> List[str]:
        """테스트할 파일 목록 반환"""
        test_files = [
            "main.py",
            "models.py", 
            "domain/langgraph/nodes/file_summarizer_node.py",
            "domain/langgraph/nodes/file_parser_node.py",
            "domain/langgraph/document_service.py",
            "app/endpoints/chat.py",
            "domain/user/service.py"
        ]
        
        # 실제 존재하는 파일만 필터링
        existing_files = []
        for file_path in test_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                existing_files.append(file_path)
            else:
                print(f"⚠️  파일이 존재하지 않음: {file_path}")
        
        return existing_files
    
    def create_test_state(self, file_paths: List[str]) -> DocumentState:
        """테스트용 DocumentState 생성"""
        state = DocumentState()
        state["repository_path"] = str(self.project_root)
        # target_files는 DocumentState에 없으므로 제거
        state["status"] = "parsing_files"
        
        return state
    
    def run_file_parser(self, state: DocumentState) -> DocumentState:
        """파일 파서 실행"""
        print("\n📁 파일 파싱 중...")
        
        # 파일 파서 노드 실행 - 테스트 파일들을 직접 설정
        # target_files 대신 직접 parsed_files를 생성
        test_files = [
            "main.py",
            "models.py", 
            "domain/langgraph/nodes/file_summarizer_node.py",
            "domain/langgraph/nodes/file_parser_node.py",
            "domain/langgraph/document_service.py"
        ]
        
        # 예시 데이터로 parsed_files 설정
        parsed_files = []
        for file_path in test_files:
            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    content = full_path.read_text(encoding='utf-8', errors='ignore')
                    parsed_files.append({
                        "file_path": file_path,
                        "language": "python",
                        "full_code": content,
                        "functions": [],
                        "classes": [],
                        "imports": [],
                        "loc": len(content.splitlines()),
                        "complexity_score": 1
                    })
                except Exception as e:
                    print(f"⚠️  파일 읽기 실패: {file_path} - {e}")
        
        state["parsed_files"] = parsed_files
        print(f"✅ {len(parsed_files)}개 파일 파싱 완료")
        
        return state
    
    def run_file_summarizer(self, state: DocumentState, use_llm: bool = True) -> DocumentState:
        """파일 요약기 실행"""
        mode = "LLM" if use_llm and self.api_key else "Mock"
        print(f"\n📝 파일 요약 중 ({mode} 모드)...")
        
        # 파일 요약기 노드 실행
        updated_state = file_summarizer_node(
            state,
            use_mock=not (use_llm and self.api_key),
            openai_api_key=self.api_key,
            include_full_code=True  # 전체 코드 포함하여 더 상세한 요약 생성
        )
        
        if "error" in updated_state:
            print(f"❌ 파일 요약 오류: {updated_state.get('error')}")
            return updated_state
        
        file_summaries = updated_state.get("file_summaries", [])
        print(f"✅ {len(file_summaries or [])}개 파일 요약 완료")
        
        return updated_state
    
    def analyze_summary_quality(self, summary: Dict[str, Any]) -> Dict[str, Any]:
        """요약 품질 분석"""
        quality_score = 0
        issues = []
        good_points = []
        
        summary_data = summary.get("summary", {})
        
        # 1. 필수 필드 존재 여부 체크
        required_fields = ["purpose", "role", "key_features"]
        missing_fields = [field for field in required_fields if not summary_data.get(field)]
        
        if not missing_fields:
            quality_score += 20
            good_points.append("모든 필수 필드가 존재함")
        else:
            issues.append(f"누락된 필드: {missing_fields}")
        
        # 2. 내용의 구체성 체크
        purpose = summary_data.get("purpose", "")
        if purpose and len(purpose) > 20:
            quality_score += 20
            good_points.append("목적 설명이 구체적임")
        else:
            issues.append("목적 설명이 너무 간단함")
        
        # 3. 주요 기능 분석
        key_features = summary_data.get("key_features", [])
        if len(key_features) >= 3:
            quality_score += 20
            good_points.append(f"{len(key_features)}개의 주요 기능 식별됨")
        else:
            issues.append("주요 기능이 충분히 식별되지 않음")
        
        # 4. 복잡도 평가 존재
        complexity = summary_data.get("complexity_assessment", "")
        if complexity and complexity != "unknown":
            quality_score += 15
            good_points.append("복잡도 평가가 수행됨")
        else:
            issues.append("복잡도 평가가 누락됨")
        
        # 5. 의존성 분석
        dependencies = summary_data.get("dependency_analysis", [])
        if dependencies:
            quality_score += 15
            good_points.append("의존성 분석이 수행됨")
        else:
            issues.append("의존성 분석이 누락됨")
        
        # 6. 유지보수성 평가
        maintainability = summary_data.get("maintainability", "")
        if maintainability and maintainability != "unknown":
            quality_score += 10
            good_points.append("유지보수성 평가가 수행됨")
        else:
            issues.append("유지보수성 평가가 누락됨")
        
        return {
            "quality_score": quality_score,
            "grade": self._get_quality_grade(quality_score),
            "good_points": good_points,
            "issues": issues
        }
    
    def _get_quality_grade(self, score: int) -> str:
        """품질 점수를 등급으로 변환"""
        if score >= 90:
            return "A+"
        elif score >= 80:
            return "A"
        elif score >= 70:
            return "B+"
        elif score >= 60:
            return "B"
        elif score >= 50:
            return "C"
        else:
            return "D"
    
    def print_summary_details(self, summary: Dict[str, Any], quality_analysis: Dict[str, Any]):
        """요약 상세 정보 출력"""
        print(f"\n📄 파일: {summary.get('file_path', 'Unknown')}")
        print(f"🔤 언어: {summary.get('language', 'Unknown')}")
        print(f"🎯 생성 방식: {summary.get('generation_method', 'Unknown')}")
        
        summary_data = summary.get("summary", {})
        
        print(f"\n📝 요약 내용:")
        print(f"  • 목적: {summary_data.get('purpose', 'Unknown')}")
        print(f"  • 역할: {summary_data.get('role', 'Unknown')}")
        print(f"  • 복잡도: {summary_data.get('complexity_assessment', 'Unknown')}")
        print(f"  • 유지보수성: {summary_data.get('maintainability', 'Unknown')}")
        
        key_features = summary_data.get('key_features', [])
        if key_features:
            print(f"  • 주요 기능:")
            for feature in key_features[:5]:  # 최대 5개만 표시
                print(f"    - {feature}")
        
        print(f"\n📊 통계:")
        print(f"  • 함수: {summary_data.get('functions_count', 0)}개")
        print(f"  • 클래스: {summary_data.get('classes_count', 0)}개")
        print(f"  • 임포트: {summary_data.get('imports_count', 0)}개")
        print(f"  • LOC: {summary_data.get('loc', 0)}줄")
        
        print(f"\n🏆 품질 평가:")
        print(f"  • 점수: {quality_analysis['quality_score']}/100")
        print(f"  • 등급: {quality_analysis['grade']}")
        
        if quality_analysis['good_points']:
            print(f"  • 장점:")
            for point in quality_analysis['good_points']:
                print(f"    ✅ {point}")
        
        if quality_analysis['issues']:
            print(f"  • 개선점:")
            for issue in quality_analysis['issues']:
                print(f"    ⚠️  {issue}")
    
    def save_test_results(self, results: List[Dict[str, Any]], filename: str | None = None):
        """테스트 결과를 파일로 저장"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"file_summarizer_test_results_{timestamp}.json"
        
        results_dir = self.project_root / "test_results"
        results_dir.mkdir(exist_ok=True)
        
        output_path = results_dir / filename
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n💾 테스트 결과 저장: {output_path}")
        
        # 마크다운 버전도 저장
        md_filename = filename.replace('.json', '.md')
        md_path = results_dir / md_filename
        self.save_markdown_report(results, md_path)
        print(f"📄 마크다운 리포트 저장: {md_path}")
    
    def save_markdown_report(self, results: List[Dict[str, Any]], output_path: Path):
        """마크다운 형식으로 테스트 결과 저장"""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# File Summarizer LLM 테스트 결과\n\n")
            f.write(f"**테스트 일시**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            # 전체 통계
            total_files = len(results)
            avg_quality = sum(r['quality_analysis']['quality_score'] for r in results) / total_files if total_files > 0 else 0
            
            f.write("## 📊 전체 통계\n\n")
            f.write(f"- **테스트 파일 수**: {total_files}개\n")
            f.write(f"- **평균 품질 점수**: {avg_quality:.1f}/100\n")
            f.write(f"- **평균 등급**: {self._get_quality_grade(int(avg_quality))}\n\n")
            
            # 파일별 상세 결과
            f.write("## 📁 파일별 상세 결과\n\n")
            
            for i, result in enumerate(results, 1):
                summary = result['summary']
                quality = result['quality_analysis']
                summary_data = summary.get('summary', {})
                
                f.write(f"### {i}. {summary.get('file_path', 'Unknown')}\n\n")
                f.write(f"- **언어**: {summary.get('language', 'Unknown')}\n")
                f.write(f"- **생성 방식**: {summary.get('generation_method', 'Unknown')}\n")
                f.write(f"- **품질 점수**: {quality['quality_score']}/100 ({quality['grade']})\n\n")
                
                f.write("#### 📝 요약 내용\n\n")
                f.write(f"**목적**: {summary_data.get('purpose', 'Unknown')}\n\n")
                f.write(f"**역할**: {summary_data.get('role', 'Unknown')}\n\n")
                
                key_features = summary_data.get('key_features', [])
                if key_features:
                    f.write("**주요 기능**:\n")
                    for feature in key_features:
                        f.write(f"- {feature}\n")
                    f.write("\n")
                
                f.write("#### 📊 통계 정보\n\n")
                f.write(f"- 함수: {summary_data.get('functions_count', 0)}개\n")
                f.write(f"- 클래스: {summary_data.get('classes_count', 0)}개\n")
                f.write(f"- 임포트: {summary_data.get('imports_count', 0)}개\n")
                f.write(f"- LOC: {summary_data.get('loc', 0)}줄\n\n")
                
                if quality['good_points']:
                    f.write("#### ✅ 장점\n\n")
                    for point in quality['good_points']:
                        f.write(f"- {point}\n")
                    f.write("\n")
                
                if quality['issues']:
                    f.write("#### ⚠️ 개선점\n\n")
                    for issue in quality['issues']:
                        f.write(f"- {issue}\n")
                    f.write("\n")
                
                f.write("---\n\n")
    
    async def run_comprehensive_test(self):
        """종합 테스트 실행"""
        print("\n" + "="*80)
        print("🧪 File Summarizer LLM 종합 테스트 시작")
        print("="*80)
        
        # 1. 테스트 파일 목록 가져오기
        test_files = self.get_test_files()
        if not test_files:
            print("❌ 테스트할 파일이 없습니다.")
            return
        
        print(f"📁 테스트 대상 파일: {len(test_files)}개")
        for file_path in test_files:
            print(f"  - {file_path}")
        
        # 2. 상태 생성 및 파일 파싱
        state = self.create_test_state(test_files)
        state = self.run_file_parser(state)
        
        error_msg = state.get("error")
        if error_msg:
            print(f"❌ 테스트 중단: {error_msg}")
            return
        
        # 3. 파일 요약 실행 (LLM 모드)
        state = self.run_file_summarizer(state, use_llm=True)
        
        error_msg = state.get("error")
        if error_msg:
            print(f"❌ 테스트 중단: {error_msg}")
            return
        
        # 4. 결과 분석
        file_summaries = state.get("file_summaries", [])
        if not file_summaries:
            print("❌ 요약 결과가 없습니다.")
            return
        
        test_results = []
        
        print(f"\n📊 요약 결과 분석 중...")
        for summary in file_summaries:
            quality_analysis = self.analyze_summary_quality(summary)
            
            result = {
                "summary": summary,
                "quality_analysis": quality_analysis,
                "timestamp": datetime.now().isoformat()
            }
            test_results.append(result)
            
            # 개별 결과 출력
            self.print_summary_details(summary, quality_analysis)
            print("\n" + "-"*60)
        
        # 5. 전체 결과 요약
        if test_results:
            avg_quality = sum(r['quality_analysis']['quality_score'] for r in test_results) / len(test_results)
            print(f"\n🏆 전체 테스트 결과:")
            print(f"  • 테스트 파일: {len(test_results)}개")
            print(f"  • 평균 품질 점수: {avg_quality:.1f}/100")
            print(f"  • 평균 등급: {self._get_quality_grade(int(avg_quality))}")
            
            # 품질별 분포
            grades = [r['quality_analysis']['grade'] for r in test_results]
            from collections import Counter
            grade_counts = Counter(grades)
            print(f"  • 등급 분포:")
            for grade in ['A+', 'A', 'B+', 'B', 'C', 'D']:
                if grade in grade_counts:
                    print(f"    - {grade}: {grade_counts[grade]}개")
        
        # 6. 결과 저장
        self.save_test_results(test_results)
        
        print(f"\n✅ 테스트 완료!")
        return test_results


async def main():
    """메인 실행 함수"""
    print("🚀 File Summarizer LLM 테스트 도구")
    print("="*50)
    
    # OpenAI API 키 확인
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("\n⚠️  환경변수에서 OPENAI_API_KEY를 찾을 수 없습니다.")
        print("Mock 모드로 실행합니다.")
        api_key = None
    
    # 테스터 생성 및 실행
    tester = FileSummarizerTester(api_key)
    await tester.run_comprehensive_test()


if __name__ == "__main__":
    asyncio.run(main())