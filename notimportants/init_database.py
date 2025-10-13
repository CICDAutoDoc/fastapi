"""
데이터베이스 초기화 및 생성 도구
"""
import os
from pathlib import Path

def create_database():
    """데이터베이스 생성"""
    print("🔧 데이터베이스 초기화를 시작합니다...")
    
    try:
        # 모듈 import
        from database import engine, Base
        import models  # 모든 모델 등록
        
        print("📦 모델과 데이터베이스 엔진 로드 완료")
        
        # 모든 테이블 생성
        Base.metadata.create_all(bind=engine)
        
        print("✅ 데이터베이스 테이블 생성 완료!")
        
        # 생성된 데이터베이스 파일 확인
        db_file = "cicd_autodoc.db"
        if os.path.exists(db_file):
            file_size = os.path.getsize(db_file)
            print(f"📄 데이터베이스 파일: {db_file} ({file_size} bytes)")
            
            # SQLite로 테이블 확인
            import sqlite3
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # 테이블 목록 조회
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            print(f"📋 생성된 테이블 ({len(tables)}개):")
            for table in tables:
                print(f"  - {table[0]}")
            
            # file_changes 테이블 구조 확인
            cursor.execute("PRAGMA table_info(file_changes)")
            columns = cursor.fetchall()
            
            print(f"\n🔍 file_changes 테이블 구조:")
            for col in columns:
                print(f"  - {col[1]} ({col[2]})")
            
            # patch 컬럼이 있는지 확인
            column_names = [col[1] for col in columns]
            if 'patch' in column_names:
                print("✅ patch 컬럼이 존재합니다!")
            else:
                print("❌ patch 컬럼이 없습니다.")
            
            conn.close()
        else:
            print("❌ 데이터베이스 파일이 생성되지 않았습니다.")
            
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 생성 실패: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_dependencies():
    """필요한 모듈들 확인"""
    print("🔍 필요한 모듈들 확인 중...")
    
    try:
        import database
        print("✅ database 모듈 OK")
        
        import models
        print("✅ models 모듈 OK")
        
        import sqlalchemy
        print(f"✅ SQLAlchemy {sqlalchemy.__version__} OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        return False

def main():
    print("🚀 CICDAutoDoc 데이터베이스 초기화")
    print("=" * 40)
    
    # 의존성 확인
    if not check_dependencies():
        print("\n❌ 필요한 모듈이 없습니다.")
        return
    
    # 데이터베이스 생성
    if create_database():
        print("\n🎉 데이터베이스 초기화 완료!")
        print("이제 FastAPI 서버를 시작할 수 있습니다.")
        print("명령어: python -m uvicorn main:app --reload --port 8001")
    else:
        print("\n❌ 초기화 실패")

if __name__ == "__main__":
    main()