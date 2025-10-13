"""
데이터베이스 초기화 스크립트
SQLite 데이터베이스에 필요한 테이블들을 생성합니다.
"""
import sys
import os
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from database import engine, Base
from app.logging_config import get_logger
import models  # 모든 모델을 임포트하여 Base.metadata에 등록

logger = get_logger("db_init")


def init_database(drop_existing: bool = False):
    """
    데이터베이스 테이블 초기화
    
    Args:
        drop_existing: 기존 테이블 삭제 여부
    """
    try:
        if drop_existing:
            logger.warning("Dropping existing tables...")
            Base.metadata.drop_all(bind=engine)
            logger.info("Existing tables dropped")
        
        # 테이블 생성
        logger.info("Creating database tables...")
        Base.metadata.create_all(bind=engine)
        
        # 생성된 테이블 목록 출력
        table_names = list(Base.metadata.tables.keys())
        logger.info(f"Database initialized successfully with {len(table_names)} tables", extra={
            "tables": table_names
        })
        
        return True
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return False


def check_database_status():
    """데이터베이스 상태 확인"""
    try:
        from sqlalchemy import inspect
        
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()
        expected_tables = list(Base.metadata.tables.keys())
        
        logger.info("Database status check", extra={
            "existing_tables": existing_tables,
            "expected_tables": expected_tables,
            "missing_tables": list(set(expected_tables) - set(existing_tables))
        })
        
        if set(expected_tables) <= set(existing_tables):
            logger.info("✅ All required tables exist")
            return True
        else:
            missing = list(set(expected_tables) - set(existing_tables))
            logger.warning(f"❌ Missing tables: {missing}")
            return False
            
    except Exception as e:
        logger.error(f"Database status check failed: {e}", exc_info=True)
        return False


def create_sample_data():
    """샘플 데이터 생성 (개발용)"""
    try:
        from database import SessionLocal
        from models import User, Repository
        from datetime import datetime
        
        session = SessionLocal()
        
        # 기존 데이터 확인
        existing_user = session.query(User).first()
        if existing_user:
            logger.info("Sample data already exists, skipping...")
            return True
        
        # 샘플 사용자 생성
        sample_user = User(
            github_id=12345,
            username="sample_user",
            email="sample@example.com",
            access_token="sample_token"  # 실제로는 암호화 필요
        )
        session.add(sample_user)
        session.commit()
        session.refresh(sample_user)
        
        # 샘플 저장소 생성
        sample_repo = Repository(
            github_id=67890,
            name="sample-repo",
            full_name="sample_user/sample-repo",
            default_branch="main",
            is_private=False,
            owner_id=sample_user.id
        )
        session.add(sample_repo)
        session.commit()
        
        logger.info("✅ Sample data created successfully", extra={
            "user_id": sample_user.id,
            "repo_id": sample_repo.id
        })
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"Sample data creation failed: {e}", exc_info=True)
        if 'session' in locals():
            session.rollback()
            session.close()
        return False


def main():
    """메인 실행 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Database initialization script")
    parser.add_argument("--drop", action="store_true", help="Drop existing tables before creating")
    parser.add_argument("--sample", action="store_true", help="Create sample data")
    parser.add_argument("--check", action="store_true", help="Check database status only")
    
    args = parser.parse_args()
    
    logger.info("Database initialization script started")
    
    if args.check:
        # 상태 확인만
        success = check_database_status()
        sys.exit(0 if success else 1)
    
    # 데이터베이스 초기화
    success = init_database(drop_existing=args.drop)
    if not success:
        logger.error("Database initialization failed")
        sys.exit(1)
    
    # 샘플 데이터 생성
    if args.sample:
        sample_success = create_sample_data()
        if not sample_success:
            logger.warning("Sample data creation failed, but database is initialized")
    
    logger.info("Database initialization completed successfully")


if __name__ == "__main__":
    main()