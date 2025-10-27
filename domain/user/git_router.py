from fastapi import APIRouter
from fastapi import Request, Header, HTTPException
from typing import Optional
from fastapi.responses import RedirectResponse
import httpx
from database import get_db
from models import User
from sqlalchemy.orm import Session
from domain.user.webhook_handler import handle_push_event, handle_pull_request_event, save_webhook_info, delete_webhook_info, get_current_user, get_user_access_token
from app.config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_AUTH_URL, GITHUB_TOKEN_URL, GITHUB_API_URL, GITHUB_WEBHOOK_SECRET

router = APIRouter(prefix="/github", tags=["Github"])





@router.get("/auth/login")
def login():
    """GitHub OAuth 로그인 시작"""
    scopes = "read:user,admin:repo_hook,repo"
    redirect_url = f"{GITHUB_AUTH_URL}?client_id={GITHUB_CLIENT_ID}&scope={scopes}"
    return RedirectResponse(redirect_url)


@router.get("/auth/callback")
async def callback(code: str):
    """GitHub OAuth 콜백 처리 및 사용자 정보 저장"""
    async with httpx.AsyncClient() as client:
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
            return {"error": "Github OAuth failed"}

        user_response = await client.get(
            GITHUB_API_URL,
            headers={"Authorization": f"token {access_token}"}
        )
        user_data = user_response.json()

    # 사용자 정보를 데이터베이스에 저장
    
    db_gen = get_db()
    db: Session = next(db_gen)
    
    try:
        # 기존 사용자 확인
        existing_user = db.query(User).filter(User.github_id == user_data["id"]).first()
        
        if existing_user:
            # 기존 사용자 토큰 업데이트
            existing_user.access_token = access_token
            existing_user.email = user_data.get("email")
            db.commit()
            user_record = existing_user
        else:
            # 새 사용자 생성
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
            
        return {
            "message": "Login successful",
            "user": {
                "id": user_record.id,
                "github_id": user_record.github_id,
                "username": user_record.username,
                "email": user_record.email
            },
            "access_token": access_token
        }
        
    except Exception as e:
        db.rollback()
        return {"error": f"Failed to save user: {str(e)}"}



@router.get("/repositories/{user_id}")
async def get_user_repositories(user_id: int):
    """사용자의 GitHub 저장소 목록 조회"""
    
    # 사용자 토큰 가져오기
    user = await get_current_user(user_id)
    access_token = await get_user_access_token(user)
    
    # 사용자 저장소 목록 가져오기
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/repos",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            params={
                "type": "owner",
                "sort": "updated",
                "per_page": 100
            }
        )

        if response.status_code == 200:
            repos = response.json()
            return {
                "repositories": [
                    {
                        "name": repo["name"],
                        "full_name": repo["full_name"],
                        "private": repo["private"],
                        "default_branch": repo["default_branch"],
                        "perm": repo["permissions"]
                    }
                    for repo in repos
                    if repo["permissions"]["admin"] # admin 권한이 있는 저장소만 가능함
                ]
            }
        else:
            return {"error": "Failed to fetch repositories"}
        
@router.get("/webhooks/{repo_owner}/{repo_name}/{user_id}")
async def list_webhooks(repo_owner: str, repo_name: str, user_id: int):
    """저장소의 웹훅 목록 조회"""
    
    # 사용자 토큰 가져오기
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
            webhooks = response.json()
            return {
                "webhooks": [
                    {
                        "id": hook["id"],
                        "name": hook["name"],
                        "active": hook["active"],
                        "events": hook["events"],
                        "config": hook["config"]
                    }
                    for hook in webhooks
                ]
            }
        else:
            return {"error": "Failed to fetch webhooks"}
        
@router.delete("/webhook/{webhook_id}/{user_id}")
async def delete_webhook(
    webhook_id: int,
    user_id: int,
    repo_owner: str,
    repo_name: str
):
    """웹훅 삭제"""
    
    # 사용자 토큰 가져오기
    user = await get_current_user(user_id)
    access_token = await get_user_access_token(user)
    
    async with httpx.AsyncClient() as client:
        response = await client.delete(
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/hooks/{webhook_id}",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        
        if response.status_code == 204:
            # 데이터베이스에서도 삭제하기
            await delete_webhook_info(webhook_id)
            return {"message": "Webhook deleted successfully"}
        else:
            return {"error": f"Failed to delete webhook: {response.status_code}"}


@router.post("/setup-repository/{user_id}")
async def setup_repository_with_webhook(
    user_id: int,
    repo_full_name: str,  # "owner/repo" 형식  
    webhook_url: str
):
    """저장소 등록 및 웹훅 설정"""
    
    try:
        # 사용자 토큰 가져오기
        user = await get_current_user(user_id)
        access_token = await get_user_access_token(user)
        # HTTP 클라이언트를 전체 함수에서 사용
        async with httpx.AsyncClient() as client:
            # 1. 저장소 정보 가져오기
            repo_response = await client.get(
                f"https://api.github.com/repos/{repo_full_name}",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json"
                }
            )
            
            if repo_response.status_code != 200:
                return {"error": f"Repository not found or no access: {repo_response.status_code}"}
            
            repo_data = repo_response.json()
            
            # admin 권한 확인
            if not repo_data.get("permissions", {}).get("admin", False):
                return {"error": "Admin permission required to set up webhook"}
            
            # 2. 웹훅 설정
            repo_owner, repo_name = repo_full_name.split("/")
            
            # 웹훅 설정
            webhook_config = {
                "name": "web",
                "active": True,
                "events": ["push", "pull_request"],
                "config": {
                    "url": f"{webhook_url.rstrip('/')}/github/webhook",
                    "content_type": "json",
                    "secret": GITHUB_WEBHOOK_SECRET,
                    "insecure_ssl": "0"
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
            
            if webhook_response.status_code != 201:
                return {
                    "error": f"Failed to create webhook: {webhook_response.status_code}",
                    "details": webhook_response.json() if webhook_response.status_code != 422 else "Webhook might already exist"
                }
            
            webhook_data = webhook_response.json()
            
            # DB에 웹훅 정보 저장
            await save_webhook_info({
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "webhook_id": webhook_data["id"],
                "webhook_url": webhook_data["config"]["url"],
                "access_token": access_token
            })
                
            return {
                "message": "Repository and webhook setup completed successfully",
                "repository": {
                    "full_name": repo_full_name,
                    "default_branch": repo_data.get("default_branch", "main"),
                    "private": repo_data.get("private", False)
                },
                "webhook": {
                    "id": webhook_data["id"],
                    "url": webhook_data["config"]["url"],
                    "message": "Webhook created successfully"
                }
            }
        
    except Exception as e:
        return {"error": f"Setup failed: {str(e)}"}



        

#웹훅 시그니쳐 검사 함수
def verify_webhook_signature(payload: bytes, signature: Optional[str]) -> bool:
    import hmac
    import hashlib

    if signature is None:
        return False

    sha_name, signature = signature.split('=')
    if sha_name != 'sha256':
        return False

    mac = hmac.new(GITHUB_WEBHOOK_SECRET.encode(), msg=payload, digestmod=hashlib.sha256)
    return hmac.compare_digest(mac.hexdigest(), signature)


@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: str = Header(...)
):
    """GitHub 웹훅 이벤트 수신 및 처리"""
    
    # 시그니처 검증
    payload = await request.body()
    if not verify_webhook_signature(payload, x_hub_signature_256):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    data = await request.json()

    # 이벤트별 처리
    if x_github_event == "push":
        return await handle_push_event(data)
    elif x_github_event == "pull_request":
        return await handle_pull_request_event(data)
    
    return {"message": "Event received", "delivery_id": x_github_delivery}
