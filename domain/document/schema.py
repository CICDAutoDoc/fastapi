from pydantic import BaseModel
from typing import Optional
from datetime import datetime

# 1. 응답 스키마 (데이터베이스에서 조회하여 클라이언트에게 전송)
class DocumentResponse(BaseModel):
    id: int
    title: str
    content: str # Markdown 내용
    summary: Optional[str] = None
    status: str
    document_type: str
    commit_sha: str
    repository_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True 

class DocumentUpdate(BaseModel):
    # 클라이언트가 주로 수정할 수 있는 필드
    title: Optional[str] = None
    content: Optional[str] = None # 편집된 Markdown 내용
    # 상태를 'EDITED' 또는 'REVIEW_DONE' 등으로 변경 요청
    status: Optional[str] = None