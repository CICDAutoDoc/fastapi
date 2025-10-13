# 🔗 GitHub OAuth 앱 설정 가이드

## 1. GitHub Developer Settings 접속

1. GitHub에 로그인 후 **Settings** → **Developer settings** → **OAuth Apps** 접속
   - 직접 링크: https://github.com/settings/applications/new

## 2. OAuth App 생성

다음 정보로 새 OAuth App을 생성하세요:

```
Application name: CICDAutoDoc FastAPI
Homepage URL: http://localhost:8000
Authorization callback URL: http://localhost:8000/github/auth/callback
Application description: 자동 문서 생성 시스템
```

## 3. Client ID와 Secret 복사

OAuth App 생성 후:

- **Client ID** 복사
- **Generate a new client secret** 클릭하여 **Client Secret** 생성 및 복사

## 4. 환경 변수 설정

`.env` 파일 생성:

```bash
# GitHub OAuth Configuration
GITHUB_CLIENT_ID=복사한_클라이언트_ID
GITHUB_CLIENT_SECRET=복사한_클라이언트_시크릿
GITHUB_WEBHOOK_SECRET=임의의_강력한_비밀번호

# OpenAI API Key (선택사항 - LLM 문서 생성용)
OPENAI_API_KEY=sk-your-openai-api-key

# Database
DATABASE_URL=sqlite:///./cicd_autodoc.db
```

## 5. 웹훅 시크릿 생성

안전한 웹훅 시크릿을 생성하세요:

```bash
# PowerShell에서 실행
-join ((1..32) | ForEach {Get-Random -input ('a'..'z') + ('A'..'Z') + ('0'..'9')})
```

## 6. ngrok 설치 및 설정

로컬 서버를 외부에서 접근할 수 있도록 ngrok 설치:

1. https://ngrok.com/download 에서 다운로드
2. 계정 생성 후 인증 토큰 설정
3. 터널 실행: `ngrok http 8000`

## 7. 프로덕션 환경에서는...

실제 서비스 시에는:

- **Homepage URL**: 실제 도메인 (예: https://yourdomain.com)
- **Callback URL**: https://yourdomain.com/github/auth/callback
- SSL 인증서 필수
- 환경 변수는 보안 관리 도구 사용
