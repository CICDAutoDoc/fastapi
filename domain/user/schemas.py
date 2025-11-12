"""
GitHub 관련 Pydantic 스키마 정의
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class SetupWebhookRequest(BaseModel):
    """웹훅 설정 요청"""
    repo_owner: str
    repo_name: str
    access_token: str
    webhook_url: str


class WebhookInfo(BaseModel):
    """웹훅 정보"""
    id: int
    name: str
    active: bool
    events: List[str]
    config: Dict[str, Any]


class WebhookResponse(BaseModel):
    """웹훅 설정 응답"""
    success: bool
    message: str
    webhook_id: Optional[int] = None
    webhook_url: Optional[str] = None
    error: Optional[str] = None


class RepositoryInfo(BaseModel):
    """저장소 정보"""
    name: str
    full_name: str
    private: bool
    default_branch: str
    permissions: Dict[str, Any]


class RepositoriesResponse(BaseModel):
    """저장소 목록 응답"""
    success: bool
    repositories: List[RepositoryInfo] = []
    total: int = 0
    error: Optional[str] = None


class WebhooksListResponse(BaseModel):
    """웹훅 목록 응답"""
    success: bool
    webhooks: List[WebhookInfo] = []
    total: int = 0
    error: Optional[str] = None


class DeleteWebhookResponse(BaseModel):
    """웹훅 삭제 응답"""
    success: bool
    message: str
    error: Optional[str] = None


class WebhookEventResponse(BaseModel):
    """웹훅 이벤트 처리 응답"""
    success: bool
    message: str
    event_type: str
    repository: Optional[str] = None
    processed: bool = False
    error: Optional[str] = None


class UserInfo(BaseModel):
    """사용자 상세 정보"""
    user_id: int
    github_id: int
    username: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    name: Optional[str] = None


class UserInfoResponse(BaseModel):
    """사용자 정보 조회 응답"""
    success: bool
    user: Optional[UserInfo] = None
    error: Optional[str] = None