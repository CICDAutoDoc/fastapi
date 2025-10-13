"""
완전한 GitHub 웹훅 자동 설정 테스트
단계별로 OAuth → 웹훅 설정까지 전체 플로우 테스트
"""
import requests
import json
import webbrowser
import time
from urllib.parse import parse_qs, urlparse

class GitHubWebhookSetup:
    def __init__(self):
        self.base_url = "http://localhost:8001"
        self.access_token = None
        
    def step1_oauth_login(self):
        """1단계: OAuth 로그인 URL 생성 및 브라우저 열기"""
        login_url = f"{self.base_url}/github/auth/login"
        print("🔐 1단계: GitHub OAuth 로그인")
        print(f"로그인 URL: {login_url}")
        print("브라우저에서 GitHub 로그인을 완료하고 callback URL에서 access_token을 복사하세요.")
        
        # 브라우저에서 로그인 페이지 열기
        webbrowser.open(login_url)
        
        return login_url
    
    def step2_get_access_token(self):
        """2단계: 사용자가 수동으로 access_token 입력"""
        print("\n📋 2단계: Access Token 입력")
        print("GitHub OAuth 로그인 후 받은 access_token을 입력하세요.")
        print("(callback URL의 응답에서 'access_token' 값을 복사)")
        
        while True:
            token = input("Access Token: ").strip()
            if token and token.startswith(('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_')):
                self.access_token = token
                print("✅ Access Token이 설정되었습니다.")
                return token
            else:
                print("❌ 올바른 GitHub access token을 입력하세요.")
    
    def step3_get_repositories(self):
        """3단계: 사용자 저장소 목록 조회"""
        if not self.access_token:
            print("❌ Access token이 없습니다.")
            return None
            
        print("\n📁 3단계: 저장소 목록 조회")
        
        try:
            response = requests.get(
                f"{self.base_url}/github/repositories",
                params={"access_token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                repos = data.get("repositories", [])
                
                print(f"✅ 관리 권한이 있는 저장소 {len(repos)}개를 찾았습니다:")
                for i, repo in enumerate(repos, 1):
                    print(f"{i}. {repo['full_name']} ({'Private' if repo['private'] else 'Public'})")
                
                return repos
            else:
                print(f"❌ 저장소 조회 실패: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None
    
    def step4_setup_webhook(self, repo_owner, repo_name, webhook_url):
        """4단계: 웹훅 자동 설정"""
        if not self.access_token:
            print("❌ Access token이 없습니다.")
            return None
            
        print(f"\n🔗 4단계: 웹훅 설정 ({repo_owner}/{repo_name})")
        print(f"웹훅 URL: {webhook_url}/github/webhook")
        
        try:
            response = requests.post(
                f"{self.base_url}/github/setup-webhook",
                params={
                    "repo_owner": repo_owner,
                    "repo_name": repo_name,
                    "access_token": self.access_token,
                    "webhook_url": webhook_url
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print("✅ 웹훅이 성공적으로 설정되었습니다!")
                print(f"웹훅 ID: {data.get('webhook')}")
                print(f"웹훅 URL: {data.get('webhook_url')}")
                return data
            else:
                print(f"❌ 웹훅 설정 실패: {response.status_code}")
                print(response.text)
                return None
                
        except Exception as e:
            print(f"❌ 오류 발생: {e}")
            return None
    
    def run_full_setup(self):
        """전체 설정 프로세스 실행"""
        print("🚀 GitHub 웹훅 자동 설정을 시작합니다!\n")
        
        # 1단계: OAuth 로그인
        self.step1_oauth_login()
        
        # 2단계: Access Token 입력
        if not self.step2_get_access_token():
            return
        
        # 3단계: 저장소 목록 조회
        repos = self.step3_get_repositories()
        if not repos:
            return
        
        # 저장소 선택
        print("\n📌 웹훅을 설정할 저장소를 선택하세요:")
        try:
            choice = int(input("저장소 번호: ")) - 1
            if 0 <= choice < len(repos):
                selected_repo = repos[choice]
                repo_owner, repo_name = selected_repo['full_name'].split('/')
            else:
                print("❌ 잘못된 선택입니다.")
                return
        except ValueError:
            print("❌ 숫자를 입력하세요.")
            return
        
        # ngrok URL 입력
        print(f"\n🌐 웹훅 URL 설정")
        print("ngrok으로 생성한 HTTPS URL을 입력하세요.")
        print("예: https://abc123.ngrok.io")
        webhook_url = input("Webhook URL: ").strip().rstrip('/')
        
        if not webhook_url.startswith('https://'):
            print("❌ HTTPS URL을 입력해야 합니다.")
            return
        
        # 4단계: 웹훅 설정
        result = self.step4_setup_webhook(repo_owner, repo_name, webhook_url)
        
        if result:
            print("\n🎉 설정 완료!")
            print("이제 해당 저장소에 push하면 웹훅 이벤트가 전송됩니다.")
        else:
            print("\n❌ 설정 실패. 다시 시도해주세요.")

if __name__ == "__main__":
    setup = GitHubWebhookSetup()
    setup.run_full_setup()