import sys
import os
import asyncio

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from domain.langgraph.document_service import get_document_service
from database import SessionLocal
from models import CodeChange, FileChange, Document

#Mock 모드로 전체 워크플로우 테스트
#OpenAI API 결제 없이 테스트 가능


def check_database():
    """DB에 테스트 데이터가 있는지 확인"""
    session = SessionLocal()
    try:
        # CodeChange 확인
        code_changes = session.query(CodeChange).all()
        print(f"\n📊 DB 상태:")
        print(f"- CodeChange 레코드 수: {len(code_changes)}")
        
        if code_changes:
            for cc in code_changes:
                print(f"\n  ID: {cc.id}")
                print(f"  SHA: {cc.commit_sha}")
                print(f"  Message: {cc.commit_message[:50]}...")
                
                file_changes = session.query(FileChange).filter(
                    FileChange.code_change_id == cc.id
                ).all()
                print(f"  FileChanges: {len(file_changes)}개")
                
                for fc in file_changes[:3]:  # 처음 3개만
                    print(f"    - {fc.filename} ({fc.status})")
        
        return len(code_changes) > 0
        
    finally:
        session.close()


async def test_mock_workflow():
    """Mock 모드로 문서 생성 테스트"""
    print("\n" + "="*60)
    print("🧪 Mock 모드 워크플로우 테스트 시작")
    print("="*60)
    
    # DB 확인
    has_data = check_database()
    
    if not has_data:
        print("\n❌ 테스트할 CodeChange 데이터가 없습니다!")
        print("Webhook으로 코드 변경사항을 먼저 등록해주세요.")
        return
    
    # Mock 모드로 DocumentService 생성
    print("\n📝 Mock 모드로 문서 생성 서비스 시작...")
    document_service = get_document_service(use_mock=True)
    
    # 첫 번째 CodeChange로 테스트
    code_change_id = 1
    
    print(f"\n🚀 CodeChange ID {code_change_id} 처리 중...")
    print("   (Mock 모드 - OpenAI API 호출 없음)")
    
    result = await document_service.process_code_change(code_change_id)
    
    print("\n" + "="*60)
    print("📊 테스트 결과")
    print("="*60)
    
    if result["success"]:
        print("✅ 문서 생성 성공!")
        print(f"\n📄 문서 정보:")
        print(f"  - Document ID: {result.get('document_id')}")
        print(f"  - Action: {result.get('action')}")
        print(f"  - Title: {result.get('title')}")
        print(f"  - Summary: {result.get('summary', '')[:100]}...")
        
        # DB에서 생성된 문서 확인
        session = SessionLocal()
        try:
            document = session.query(Document).filter(
                Document.id == result['document_id']
            ).first()
            
            if document:
                print(f"\n📖 생성된 문서 내용 미리보기:")
                print("-" * 60)
                content_preview = document.content[:500] if document.content else "내용 없음"
                print(content_preview)
                if len(document.content) > 500:
                    print("\n... (생략) ...")
                print("-" * 60)
                
                print(f"\n💾 DB 저장 정보:")
                print(f"  - Status: {document.status}")
                print(f"  - Type: {document.document_type}")
                print(f"  - Created: {document.created_at}")
        finally:
            session.close()
            
    else:
        print("❌ 문서 생성 실패!")
        print(f"Error: {result.get('error')}")
    
    print("\n" + "="*60)
    print("✅ Mock 모드 테스트 완료!")
    print("="*60)
    print("\n💡 참고:")
    print("  - Mock 모드는 실제 OpenAI API를 호출하지 않습니다")
    print("  - 테스트용 더미 데이터를 사용합니다")
    print("  - 실제 문서 품질을 확인하려면 OpenAI API 결제 후 test_workflow.py를 실행하세요")


if __name__ == "__main__":
    asyncio.run(test_mock_workflow())
