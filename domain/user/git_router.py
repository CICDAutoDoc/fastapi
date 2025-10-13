from fastapi import APIRouter
from fastapi import Request, Header, HTTPException
from typing import Optional
from fastapi.responses import RedirectResponse
import httpx
from domain.user.webhook_handler import handle_push_event, handle_pull_request_event, save_webhook_info, delete_webhook_info
from app.config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_AUTH_URL, GITHUB_TOKEN_URL, GITHUB_API_URL, GITHUB_WEBHOOK_SECRET

router = APIRouter(prefix="/github", tags=["Github"])


@router.get("/auth/login")
def login():
    scopes = "read:user,admin:repo_hook,repo"
    rediect_url = f"{GITHUB_AUTH_URL}?client_id={GITHUB_CLIENT_ID}&scope={scopes}"
    return RedirectResponse(rediect_url)


@router.get("/auth/callback")
async def callback(code: str):
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

    return {
        "GitHub User": user_data,
        "access_token": access_token  # 토큰도 함께 반환
    }

@router.post("/setup-webhook")
async def setup_webhook(
    repo_owner: str,
    repo_name: str,
    access_token: str,
    webhook_url: str
):
    #깃허브 저장소에 webhook 자동 등록
    webhook_config = {
        "name": "web",
        "active": True,
        "events": ["push", "pull_request"], # main branch merge를 알기 위해서
        "config": {
            "url": f"{webhook_url}/github/webhook",
            "content_type": "json",
            "secret": GITHUB_WEBHOOK_SECRET,
            "insecure_ssl": "0" #https 필수로 사용하도록
        }
    
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://api.github.com/repos/{repo_owner}/{repo_name}/hooks",
            headers={
                "Authorization": f"token {access_token}",
                "Accept": "application/vnd.github.v3+json"
            },
            json=webhook_config
        )
        if response.status_code == 201:
            webhook_data = response.json()

            #데이터베이스에 webhook 정보 저장
            await save_webhook_info({
                "repo_owner": repo_owner,
                "repo_name": repo_name,
                "webhook_id": webhook_data["id"],
                "webhook_url": webhook_data["config"]["url"],
                "access_token": access_token  # 암호화해서 저장 필요
            })

            return{
                "message": "Webhook created successfully",
                "webhook": webhook_data['id'],
                "webhook_url": webhook_data['config']['url']
            }
        else:
            return {
                "error": f"Failed to create webhook: {response.status_code}",
                "details": response.json()
            }
        

@router.get("/repositories")
async def get_user_repositories(access_token: str):
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
        
@router.get("/webhooks/{repo_owner}/{repo_name}")
async def list_webhooks(repo_owner: str, repo_name: str, access_token: str):
    #저장소의 기존에 있는 webhook 목록을 조회하기
    
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
        
@router.delete("/webhook/{webhook_id}")
async def delete_webhook(
    webhook_id: int,
    repo_owner: str,
    repo_name: str,
    access_token: str
):
    #Webhook 삭제 하기
    
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


#GitHub webhook 수신 처리
@router.post("/webhook")
async def github_webhook(
    request: Request,
    x_github_event: str = Header(...),
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_delivery: str = Header(...)
):
    
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
