from fastapi import APIRouter
from fastapi.responses import RedirectResponse
import httpx
from app.config import GITHUB_CLIENT_ID, GITHUB_CLIENT_SECRET, GITHUB_AUTH_URL, GITHUB_TOKEN_URL, GITHUB_API_URL

router = APIRouter(prefix="/github", tags=["Github"])


@router.get("/auth/login")
def login():
    rediect_url = f"{GITHUB_AUTH_URL}?client_id={GITHUB_CLIENT_ID}&scope=read:user"
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

    return {"GitHub User": user_data}