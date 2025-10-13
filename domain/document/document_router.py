"""
문서 관련 API 라우터
프론트엔드에서 생성된 문서를 조회하고 관리하는 엔드포인트들
"""
from fastapi import APIRouter, HTTPException, Query, Path
from typing import List, Dict, Any, Optional
from domain.langgraph.document_service import get_document_service

router = APIRouter(prefix="/documents", tags=["Documents"])


@router.get("/", response_model=List[Dict[str, Any]])
async def get_documents(
    repository: Optional[str] = Query(None, description="저장소 이름으로 필터링"),
    limit: int = Query(20, ge=1, le=100, description="가져올 문서 수"),
    offset: int = Query(0, ge=0, description="건너뛸 문서 수")
):
    """
    문서 목록 조회
    
    - **repository**: 특정 저장소의 문서만 조회 (선택사항)
    - **limit**: 한 번에 가져올 문서 수 (1-100)
    - **offset**: 페이징을 위한 오프셋
    """
    try:
        document_service = get_document_service()
        documents = document_service.get_documents(
            repository_name=repository,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "data": documents,
            "total": len(documents),
            "filters": {
                "repository": repository,
                "limit": limit,
                "offset": offset
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch documents: {str(e)}")


@router.get("/{document_id}", response_model=Dict[str, Any])
async def get_document_detail(
    document_id: int = Path(..., description="문서 ID")
):
    """
    문서 상세 조회
    
    - **document_id**: 조회할 문서의 ID
    """
    try:
        document_service = get_document_service()
        document = document_service.get_document_detail(document_id)
        
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        return {
            "success": True,
            "data": document
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch document: {str(e)}")


@router.get("/repository/{repository_name}", response_model=List[Dict[str, Any]])
async def get_repository_documents(
    repository_name: str = Path(..., description="저장소 이름 (owner/repo 형식)"),
    limit: int = Query(20, ge=1, le=100, description="가져올 문서 수"),
    offset: int = Query(0, ge=0, description="건너뛸 문서 수")
):
    """
    특정 저장소의 문서 목록 조회
    
    - **repository_name**: 저장소 이름 (예: "username/repository")
    - **limit**: 한 번에 가져올 문서 수
    - **offset**: 페이징을 위한 오프셋
    """
    try:
        document_service = get_document_service()
        documents = document_service.get_documents(
            repository_name=repository_name,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "repository": repository_name,
            "data": documents,
            "total": len(documents)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch repository documents: {str(e)}")


@router.post("/generate/{code_change_id}")
async def generate_document_manually(
    code_change_id: int = Path(..., description="코드 변경 ID")
):
    """
    수동으로 문서 생성/재생성
    
    - **code_change_id**: 문서를 생성할 코드 변경사항 ID
    """
    try:
        document_service = get_document_service()
        result = await document_service.process_code_change(code_change_id)
        
        if result["success"]:
            return {
                "success": True,
                "message": f"Document {result['action']} successfully",
                "data": {
                    "document_id": result["document_id"],
                    "title": result.get("title"),
                    "summary": result.get("summary"),
                    "action": result["action"]
                }
            }
        else:
            raise HTTPException(
                status_code=400, 
                detail=f"Document generation failed: {result.get('error', 'Unknown error')}"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate document: {str(e)}")


@router.get("/stats/summary")
async def get_document_stats():
    """
    문서 생성 통계 조회
    """
    try:
        from database import SessionLocal
        from models import Document
        from sqlalchemy import func
        
        session = SessionLocal()
        try:
            # 기본 통계
            total_docs = session.query(Document).count()
            generated_docs = session.query(Document).filter(Document.status == "generated").count()
            failed_docs = session.query(Document).filter(Document.status == "failed").count()
            
            # 저장소별 통계
            repo_stats = session.query(
                Document.repository_name,
                func.count(Document.id).label('count')
            ).group_by(Document.repository_name).all()
            
            # 최근 문서들
            recent_docs = session.query(Document).order_by(
                Document.created_at.desc()
            ).limit(5).all()
            
            return {
                "success": True,
                "stats": {
                    "total_documents": total_docs,
                    "generated_documents": generated_docs,
                    "failed_documents": failed_docs,
                    "success_rate": round(generated_docs / max(total_docs, 1) * 100, 2)
                },
                "repository_stats": [
                    {"repository": repo, "count": count} 
                    for repo, count in repo_stats
                ],
                "recent_documents": [
                    {
                        "id": doc.id,
                        "title": doc.title,
                        "repository": doc.repository_name,
                        "status": doc.status,
                        "created_at": doc.created_at.isoformat() if doc.created_at is not None else None
                    }
                    for doc in recent_docs
                ]
            }
        finally:
            session.close()
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {str(e)}")


# 헬스 체크 엔드포인트
@router.get("/health")
async def health_check():
    """
    문서 시스템 상태 확인
    """
    try:
        # 문서 서비스 상태 확인
        document_service = get_document_service()
        
        # 간단한 데이터베이스 연결 테스트
        from database import SessionLocal
        session = SessionLocal()
        try:
            # 테이블 존재 확인
            from models import Document
            session.query(Document).first()
        finally:
            session.close()
        
        return {
            "success": True,
            "status": "healthy",
            "message": "Document system is operational",
            "timestamp": "2023-10-13T12:00:00Z"
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, 
            detail=f"Document system is not healthy: {str(e)}"
        )