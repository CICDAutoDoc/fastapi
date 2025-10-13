from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from domain.user import git_router
from domain.document import document_router
from app.logging_config import get_logger, setup_logging_from_env

# 로깅 초기화
setup_logging_from_env()
logger = get_logger("main")

app = FastAPI()

origins = [
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(git_router.router)
app.include_router(document_router.router)


@app.on_event("startup")
async def startup_event():
    """앱 시작시 실행되는 초기화 작업"""
    logger.info("Starting CICDAutoDoc API server...")
    
    # 데이터베이스 초기화
    try:
        from database import engine, Base
        import models  # 모든 모델 등록
        
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized")
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        # 데이터베이스 초기화 실패해도 서버는 시작 (개발환경 고려)
    
    logger.info("CICDAutoDoc API server started successfully")


@app.on_event("shutdown") 
async def shutdown_event():
    """앱 종료시 정리 작업"""
    logger.info(" Shutting down CICDAutoDoc API server...")
    logger.info(" CICDAutoDoc API server stopped")