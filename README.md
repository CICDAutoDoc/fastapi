# 🚀 CICDAutoDoc

GitHub 저장소의 **자동 AI 문서화** 시스템입니다. 코드 변경사항을 실시간으로 감지하고 OpenAI GPT를 활용하여 자동으로 문서를 생성합니다.

## ✨ 주요 기능

- 🔄 **실시간 웹훅 처리**: GitHub Push 이벤트 자동 감지
- 🤖 **AI 문서 생성**: OpenAI GPT-4o-mini 기반 고품질 문서 자동 생성
- 📚 **저장소별 문서 관리**: 커밋별 변경사항을 누적하여 종합 문서 생성
- 🔐 **GitHub OAuth 통합**: 안전한 GitHub 계정 연동
- 📡 **RESTful API**: 프론트엔드 연동을 위한 완전한 API 제공

## 🛠️ 기술 스택

- **Backend**: FastAPI (Python 3.8+)
- **Database**: SQLite with SQLAlchemy ORM
- **AI**: OpenAI GPT-4o-mini + LangGraph StateGraph
- **Authentication**: GitHub OAuth 2.0
- **Webhook**: GitHub Webhooks for real-time events

## 📋 필수 요구사항

- Python 3.8 이상
- GitHub OAuth App (Client ID, Client Secret)
- OpenAI API Key
- 인터넷 연결 (GitHub API, OpenAI API 호출용)

## ⚡ 빠른 시작

### 1. 저장소 클론

```bash
git clone https://github.com/your-username/CICDAutoDoc.git
cd CICDAutoDoc/fastapi
```

### 2. 가상환경 생성 및 활성화

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 또는
venv\Scripts\activate  # Windows
```

### 3. 의존성 설치

```bash
pip install -r requirements.txt
```

### 4. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일을 열어서 실제 값들로 수정
```

### 5. 서버 실행

```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## 환경 설정

### GitHub OAuth App 생성

1. GitHub Settings > Developer settings > OAuth Apps
2. New OAuth App 클릭
3. 다음 정보 입력:
   - **Application name**: CICDAutoDoc
   - **Homepage URL**: `http://localhost:8000`
   - **Authorization callback URL**: `http://localhost:8000/auth/callback`
4. Client ID와 Client Secret을 `.env` 파일에 입력

### OpenAI API 키 발급

1. [OpenAI Platform](https://platform.openai.com/api-keys)에서 API 키 생성
2. `.env` 파일의 `OPENAI_API_KEY`에 입력

### .env 파일 예시

```env
# GitHub OAuth Configuration
GITHUB_CLIENT_ID=your_actual_client_id
GITHUB_CLIENT_SECRET=your_actual_client_secret
GITHUB_WEBHOOK_SECRET=your_secure_webhook_secret

# OpenAI Configuration
OPENAI_API_KEY=sk-your-actual-api-key

# Database Configuration
DATABASE_URL=sqlite:///./cicd_autodoc.db

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true
```

## 📡 API 엔드포인트

### 인증

- `GET /auth/github` - GitHub OAuth 시작
- `POST /auth/callback` - OAuth 콜백 처리

### 저장소 관리

- `GET /repositories` - 사용자 저장소 목록
- `GET /webhooks/{owner}/{repo}` - 웹훅 목록 조회
- `POST /webhooks/{owner}/{repo}` - 웹훅 등록
- `DELETE /webhooks/{owner}/{repo}/{webhook_id}` - 웹훅 삭제

### 문서 관리

- `GET /documents/` - 생성된 문서 목록
- `GET /documents/{document_id}` - 특정 문서 조회
- `POST /documents/generate/{code_change_id}` - 수동 문서 생성
- `GET /documents/stats/summary` - 문서 통계

### 웹훅

- `POST /webhook/github` - GitHub 웹훅 수신

## 🚀 사용 방법

1. **서버 실행** 후 `http://localhost:8000` 접속
2. **GitHub 로그인** 수행
3. **저장소 선택** 및 웹훅 등록
4. **코드 Push** → 자동 문서 생성!

## 📊 데이터베이스 구조

- **users**: GitHub 사용자 정보
- **repositories**: 연동된 저장소 정보
- **webhook_registrations**: 등록된 웹훅 정보
- **code_changes**: 커밋별 코드 변경사항
- **file_changes**: 파일별 상세 변경사항
- **documents**: AI가 생성한 문서

## 🧪 테스트

```bash
# 단위 테스트 실행
pytest

# 특정 테스트 실행
pytest test/test_document_service.py

# 커버리지 포함 테스트
pytest --cov=domain
```

## 📝 라이센스

MIT License - 자세한 내용은 [LICENSE](LICENSE) 파일을 참고하세요.

## 🤝 기여하기

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 🔗 관련 링크

- [GitHub OAuth Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
