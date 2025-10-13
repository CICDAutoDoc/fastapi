"""
데이터베이스 스키마 업데이트 도구
file_changes 테이블에 patch 컬럼 추가
"""
import sqlite3
import os
from pathlib import Path

def fix_database_schema():
    """데이터베이스 스키마 수정"""
    
    # 데이터베이스 파일 경로
    db_path = "cicd_autodoc.db"
    
    print(f"🔧 데이터베이스 스키마 수정: {db_path}")
    
    # 데이터베이스 파일이 존재하는지 확인
    if not os.path.exists(db_path):
        print("❌ 데이터베이스 파일이 없습니다. 새로 생성됩니다.")
        return False
    
    try:
        # 데이터베이스 연결
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 현재 file_changes 테이블 구조 확인
        cursor.execute("PRAGMA table_info(file_changes)")
        columns = cursor.fetchall()
        
        print("📋 현재 file_changes 테이블 구조:")
        column_names = []
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
            column_names.append(col[1])
        
        # patch 컬럼이 있는지 확인
        if 'patch' in column_names:
            print("✅ patch 컬럼이 이미 존재합니다.")
            conn.close()
            return True
        
        # patch 컬럼 추가
        print("\n🔨 patch 컬럼 추가 중...")
        cursor.execute("ALTER TABLE file_changes ADD COLUMN patch TEXT")
        conn.commit()
        
        print("✅ patch 컬럼이 성공적으로 추가되었습니다!")
        
        # 변경된 구조 확인
        cursor.execute("PRAGMA table_info(file_changes)")
        columns = cursor.fetchall()
        
        print("\n📋 수정된 file_changes 테이블 구조:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 수정 실패: {e}")
        return False

def backup_database():
    """데이터베이스 백업"""
    db_path = "cicd_autodoc.db"
    
    if not os.path.exists(db_path):
        print("백업할 데이터베이스가 없습니다.")
        return
    
    backup_path = f"{db_path}.backup"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ 데이터베이스 백업 완료: {backup_path}")
    except Exception as e:
        print(f"❌ 백업 실패: {e}")

def recreate_database():
    """데이터베이스 완전 재생성"""
    db_path = "cicd_autodoc.db"
    
    print("⚠️  데이터베이스를 완전히 재생성합니다. 모든 데이터가 삭제됩니다!")
    choice = input("계속하시겠습니까? (y/N): ").strip().lower()
    
    if choice != 'y':
        print("취소되었습니다.")
        return False
    
    try:
        # 기존 데이터베이스 삭제
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"🗑️  기존 데이터베이스 삭제: {db_path}")
        
        # 새 데이터베이스는 FastAPI 시작시 자동 생성됨
        print("✅ 데이터베이스 재생성 준비 완료")
        print("FastAPI 서버를 다시 시작하면 새로운 스키마로 데이터베이스가 생성됩니다.")
        
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 재생성 실패: {e}")
        return False

def main():
    """메인 함수"""
    print("🛠️  CICDAutoDoc 데이터베이스 스키마 수정 도구")
    print("=" * 50)
    
    print("\n선택하세요:")
    print("1. patch 컬럼 추가 (권장)")
    print("2. 데이터베이스 완전 재생성 (모든 데이터 삭제)")
    print("3. 데이터베이스 백업만 생성")
    print("4. 취소")
    
    choice = input("\n선택 (1-4): ").strip()
    
    if choice == '1':
        # 백업 먼저 생성
        backup_database()
        
        # 스키마 수정
        if fix_database_schema():
            print("\n🎉 데이터베이스 수정 완료!")
            print("이제 FastAPI 서버를 다시 시작하면 웹훅이 정상 작동할 것입니다.")
        else:
            print("\n❌ 수정 실패. 옵션 2를 시도해보세요.")
            
    elif choice == '2':
        backup_database()
        recreate_database()
        
    elif choice == '3':
        backup_database()
        
    elif choice == '4':
        print("취소되었습니다.")
        
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()