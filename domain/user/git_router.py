from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional, List
from fastapi.responses import RedirectResponse, JSONResponse
import httpx
from sqlalchemy.orm import Session

# schemas.py 파일에서 정의한 Pydantic 모델들을 가져옵니다.
from domain.user.schemas import *
from database import get_db
from models import User
from domain.user.webhook_handler import (
    handle_push_event, handle_pull_request_event, save_webhook_info,
    delete_webhook_info, get_current_user, get_user_access_token
)
from app.config import (
    GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_AUTH_URL,
    GITHUB_TOKEN_URL, GITHUB_API_URL, GITHUB_WEBHOOK_SECRET
)

# 태그(tags)를 기능별로 분리하여 API를 그룹화합니다.
# main.py에서 태그에 대한 설명을 추가하면 더 상세한 문서화가 가능합니다.
router = APIRouter(prefix="/github")


# --- Authentication ---

@router.get(
    "/auth/login",
    tags=["Authentication"],
    summary="GitHub OAuth 로그인 시작",
    description="사용자를 GitHub OAuth 인증 페이지로 리디렉션하여 로그인을 시작합니다. 'repo' 및 'admin:repo_hook' 스코프 권한을 요청합니다."
)
def login():
    """GitHub OAuth 로그인 시작"""
    scopes = "read:user,admin:repo_hook,repo"
    redirect_url = f"{GITHUB_AUTH_URL}?client_id={GITHUB_CLIENT_ID}&scope={scopes}"
    return RedirectResponse(redirect_url)


@router.get(
    "/auth/callback",
    tags=["Authentication"],
    summary="GitHub OAuth 콜백 처리",
    description="GitHub로부터 인증 코드를 받아 액세스 토큰을 요청하고, 사용자 정보를 DB에 저장하거나 업데이트합니다."
)
async def callback(code: str):
    """GitHub OAuth 콜백 처리 및 사용자 정보 저장"""
    async with httpx.AsyncClient() as client:
        # 액세스 토큰 요청
        response = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": GITHUB_CLIENT_ID,
                "client_secret": GITHUB_CLIENT_SECRET,
                "code": code
            }
        )
        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Github OAuth failed")

        # 사용자 정보 요청
        user_response = await client.get(
            GITHUB_API_URL,
            headers={"Authorization": f"token {access_token}"}
        )
        user_data = user_response.json()

    # 사용자 정보 데이터베이스에 저장
    db: Session = next(get_db())
    try:
        existing_user = db.query(User).filter_by(github_id=user_data["id"]).first()
        if existing_user:
            existing_user.access_token = access_token
            existing_user.email = user_data.get("email")
            db.commit()
            user_record = existing_user
        else:
            new_user = User(
                github_id=user_data["id"],
                username=user_data["login"],
                email=user_data.get("email"),
                access_token=access_token
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            user_record = new_user

        # 성공 응답 반환
        return JSONResponse(status_code=200, content={
            "message": "Login successful",
            "user": {
                "id": user_record.id,
                "github_id": user_record.github_id,
                "username": user_record.username,
                "email": user_record.email
            },
            "access_token": access_token
        })
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save user: {str(e)}")
    finally:
        db.close()


# --- Repositories ---

@router.get(
    "/repositories/{user_id}",
    tags=["Repositories"],
    response_model=RepositoriesResponse,
    summary="사용자의 GitHub 저장소 목록 조회",
    description="사용자 ID를 기반으로 해당 사용자가 'admin' 권한을 가진 모든 저장소 목록을 조회합니다."
)
async def get_user_repositories(user_id: int):
    """사용자의 GitHub 저장소 목록 조회"""
    try:
        user = await get_current_user(user_id)
        access_token = await get_user_access_token(user)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/user/repos",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                params={"type": "owner", "sort": "updated", "per_page": 100}
            )

            if response.status_code == 200:
                repos = response.json()
                admin_repos = [
                    RepositoryInfo(
                        name=repo["name"],
                        full_name=repo["full_name"],
                        private=repo["private"],
                        default_branch=repo["default_branch"],
                        permissions=repo["permissions"]
                    )
                    for repo in repos if repo.get("permissions", {}).get("admin")
                ]
                return RepositoriesResponse(
                    success=True,
                    repositories=admin_repos,
                    total=len(admin_repos)
                )
            else:
                return RepositoriesResponse(success=False,
                                                    error=f"Failed to fetch repositories: {response.status_code}")
    except Exception as e:
        return RepositoriesResponse(success=False, error=str(e))


# --- Webhooks ---

@router.get(
    "/webhooks/{repo_owner}/{repo_name}/{user_id}",
    tags=["Webhooks"],
    response_model=WebhooksListResponse,
    summary="저장소의 웹훅 목록 조회",
    description="특정 저장소에 등록된 모든 웹훅의 목록을 조회합니다."
)
async def list_webhooks(repo_owner: str, repo_name: str, user_id: int):
    """저장소의 웹훅 목록 조회"""
    try:
        user = await get_current_user(user_id)
        access_token = await get_user_access_token(user)

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/hooks",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )

            if response.status_code == 200:
                webhooks_data = response.json()
                webhooks_list = [WebhookInfo(**hook) for hook in webhooks_data]
                return WebhooksListResponse(
                    success=True,
                    webhooks=webhooks_list,
                    total=len(webhooks_list)
                )
            else:
                return WebhooksListResponse(success=False,
                                                    error=f"Failed to fetch webhooks: {response.status_code}")
    except Exception as e:
        return WebhooksListResponse(success=False, error=str(e))


@router.post(
    "/setup-repository/{user_id}",
    tags=["Webhooks"],
    response_model=WebhookResponse,
    summary="저장소 등록 및 웹훅 설정",
    description="''owner/repo' 형식의 저장소 전체 이름과 웹훅 URL을 받아 저장소를 등록하고, 'push' 및 'pull_request' 이벤트를 구독하는 웹훅을 자동으로 설정합니다."
)
async def setup_repository_with_webhook(request: SetupWebhookRequest, user_id: int):
    """저장소 등록 및 웹훅 설정"""
    try:
        user = await get_current_user(user_id)
        access_token = await get_user_access_token(user)
        repo_owner, repo_name = request.repo_owner, request.repo_name
        repo_full_name = f"{repo_owner}/{repo_name}"

        async with httpx.AsyncClient() as client:
            # 웹훅 설정
            webhook_config = {
                "name": "web",
                "active": True,
                "events": ["push", "pull_request"],
                "config": {
                    "url": f"{request.webhook_url.rstrip('/')}/github/webhook",
                    "content_type": "json",
                    "secret": GITHUB_WEBHOOK_SECRET
                }
            }

            webhook_response = await client.post(
                f"https://api.github.com/repos/{repo_full_name}/hooks",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                },
                json=webhook_config
            )

            if webhook_response.status_code not in [200, 201]:
                details = webhook_response.json()
                error_msg = details.get("message", "Failed to create webhook")
                if "Hook already exists" in str(details):
                    error_msg = "Webhook might already exist on this repository."
                return WebhookResponse(success=False, message=error_msg, error=str(details))

            webhook_data = webhook_response.json()

            # DB에 웹훅 정보 저장
            await save_webhook_info({
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "webhook_id": webhook_data["id"],
                "webhook_url": webhook_data["config"]["url"],
                "access_token": access_token
            })

            return WebhookResponse(
                success=True,
                message="Webhook setup completed successfully.",
                webhook_id=webhook_data["id"],
                webhook_url=webhook_data["config"]["url"]
            )
    except Exception as e:
        return WebhookResponse(success=False, message="An unexpected error occurred during webhook setup.",
                                       error=str(e))


@router.delete(
    "/webhook/{repo_owner}/{repo_name}/{webhook_id}/{user_id}",
    tags=["Webhooks"],
    response_model=DeleteWebhookResponse,
    summary="GitHub 웹훅 삭제",
    description="저장소에 등록된 특정 웹훅을 ID를 이용해 삭제합니다."
)
async def delete_webhook(repo_owner: str, repo_name: str, webhook_id: int, user_id: int):
    """웹훅 삭제"""
    try:
        user = await get_current_user(user_id)
        access_token = await get_user_access_token(user)

        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"https://api.github.com/repos/{repo_owner}/{repo_name}/hooks/{webhook_id}",
                headers={"Authorization": f"token {access_token}"}
            )

            if response.status_code == 204:
                await delete_webhook_info(webhook_id)
                return DeleteWebhookResponse(success=True, message="Webhook deleted successfully.")
            else:
                return DeleteWebhookResponse(success=False, message="Failed to delete webhook.",
                                                     error=f"Status: {response.status_code}, Response: {response.text}")
    except Exception as e:
        return DeleteWebhookResponse(success=False, message="An unexpected error occurred.", error=str(e))


def verify_webhook_signature(payload: bytes, signature: Optional[str]) -> bool:
    # ... (기존과 동일)
    import hmac, hashlib
    if signature is None: return False
    sha_name, signature_hex = signature.split('=')
    if sha_name != 'sha256': return False
    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature_hex)


@router.post(
    "/webhook",
    tags=["Webhooks"],
    response_model=WebhookEventResponse,
    summary="GitHub 웹훅 이벤트 수신",
    description="GitHub로부터 'push', 'pull_request' 등의 이벤트를 수신하고, 시그니처를 검증한 후 각 이벤트에 맞는 핸들러로 처리를 위임합니다."
)
async def github_webhook(
        request: Request,
        x_github_event: str = Header(...),
        x_github_delivery: str = Header(...),
        x_hub_signature_256: Optional[str] = Header(None)
):
    """GitHub 웹훅 이벤트 수신 및 처리"""
    payload = await request.body()
    if not verify_webhook_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")

    data = await request.json()

    if x_github_event == "push":
        return await handle_push_event(data)
    elif x_github_event == "pull_request":
        return await handle_pull_request_event(data)

    return WebhookEventResponse(
        success=True,
        message="Event received but not handled.",
        event_type=x_github_event,
        processed=False
    )
