"""
데이터베이스 초기화 스크립트
모든 테이블의 데이터를 삭제하고 깨끗한 상태로 만듭니다.
"""
import os
from database import SessionLocal, engine
from models import Base, CodeChange, Document, FileChange

def clear_database():
    """데이터베이스의 모든 데이터를 삭제"""
    
    print("🗄️ 데이터베이스 초기화")
    print("=" * 50)
    
    session = SessionLocal()
    try:
        # 1. 현재 상태 확인
        print("1. 📊 현재 데이터베이스 상태:")
        
        code_changes_count = session.query(CodeChange).count()
        documents_count = session.query(Document).count()
        file_changes_count = session.query(FileChange).count()
        
        print(f"   - CodeChange: {code_changes_count}개")
        print(f"   - Document: {documents_count}개")
        print(f"   - FileChange: {file_changes_count}개")
        
        total_records = code_changes_count + documents_count + file_changes_count
        
        if total_records == 0:
            print("   ✅ 데이터베이스가 이미 비어있습니다.")
            return True
        
        # 2. 사용자 확인
        print(f"\n⚠️  총 {total_records}개의 레코드가 삭제됩니다.")
        confirm = input("정말로 모든 데이터를 삭제하시겠습니까? (y/N): ").strip().lower()
        
        if confirm != 'y':
            print("   🚫 데이터베이스 초기화가 취소되었습니다.")
            return False
        
        # 3. 데이터 삭제 (순서 중요: 외래 키 제약조건 고려)
        print(f"\n2. 🗑️  데이터 삭제 중...")
        
        # FileChange 먼저 삭제 (CodeChange를 참조)
        deleted_files = session.query(FileChange).delete()
        print(f"   ✅ FileChange: {deleted_files}개 삭제")
        
        # Document 삭제 (CodeChange를 참조)
        deleted_docs = session.query(Document).delete()
        print(f"   ✅ Document: {deleted_docs}개 삭제")
        
        # CodeChange 마지막 삭제
        deleted_changes = session.query(CodeChange).delete()
        print(f"   ✅ CodeChange: {deleted_changes}개 삭제")
        
        # 4. 변경사항 커밋
        session.commit()
        print(f"\n   💾 데이터베이스 변경사항 저장 완료")
        
        # 5. 확인
        print(f"\n3. ✅ 초기화 완료 확인:")
        
        final_code_changes = session.query(CodeChange).count()
        final_documents = session.query(Document).count()
        final_file_changes = session.query(FileChange).count()
        
        print(f"   - CodeChange: {final_code_changes}개")
        print(f"   - Document: {final_documents}개")
        print(f"   - FileChange: {final_file_changes}개")
        
        if final_code_changes == 0 and final_documents == 0 and final_file_changes == 0:
            print(f"\n🎉 데이터베이스 초기화가 성공적으로 완료되었습니다!")
            return True
        else:
            print(f"\n❌ 일부 데이터가 남아있습니다. 수동 확인이 필요합니다.")
            return False
            
    except Exception as e:
        session.rollback()
        print(f"\n❌ 데이터베이스 초기화 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        session.close()

def recreate_tables():
    """테이블을 완전히 재생성"""
    
    print("\n4. 🔄 테이블 재생성...")
    
    try:
        # 모든 테이블 삭제
        Base.metadata.drop_all(bind=engine)
        print("   ✅ 기존 테이블 삭제 완료")
        
        # 모든 테이블 재생성
        Base.metadata.create_all(bind=engine)
        print("   ✅ 새 테이블 생성 완료")
        
        return True
        
    except Exception as e:
        print(f"   ❌ 테이블 재생성 중 오류: {e}")
        return False

def main():
    """메인 함수"""
    
    try:
        print("🚀 CICDAutoDoc 데이터베이스 초기화 도구")
        print("=" * 60)
        
        # 옵션 선택
        print("\n초기화 방법을 선택하세요:")
        print("1. 데이터만 삭제 (테이블 구조 유지)")
        print("2. 테이블 완전 재생성 (구조까지 새로 생성)")
        print("3. 취소")
        
        choice = input("\n선택 (1-3): ").strip()
        
        if choice == '1':
            success = clear_database()
            
        elif choice == '2':
            success = clear_database()
            if success:
                success = recreate_tables()
                
        elif choice == '3':
            print("🚫 초기화가 취소되었습니다.")
            return
            
        else:
            print("❌ 잘못된 선택입니다.")
            return
        
        if success:
            print(f"\n🎯 다음 단계:")
            print(f"   1. FastAPI 서버 실행: uvicorn main:app --host 0.0.0.0 --port 8001 --reload")
            print(f"   2. GitHub 웹훅을 통한 새 데이터 생성")
            print(f"   3. 실제 LLM 문서 생성 테스트")
            print(f"\n✨ 깨끗한 상태에서 다시 시작할 준비가 되었습니다!")
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  사용자가 초기화를 중단했습니다.")
    except Exception as e:
        print(f"\n\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()