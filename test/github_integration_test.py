"""
CICDAutoDoc GitHub 통합 테스트
git_router.py의 모든 기능을 테스트하는 통합 도구

기능:
1. GitHub OAuth 로그인
2. 저장소 목록 조회
3. 웹훅 등록/조회/삭제
4. 웹훅 이벤트 처리 테스트
"""
import requests
import json
import webbrowser
import time
from urllib.parse import urlparse, parse_qs

class CICDAutoDocTester:
    def __init__(self):
        self.base_url = "http://localhost:8000"
        self.access_token = None
        self.selected_repo = None
        self.current_webhooks = []
        
    def clear_screen(self):
        """화면 정리"""
        print("\n" + "="*80)
        
    def print_header(self, title):
        """헤더 출력"""
        self.clear_screen()
        print(f"🚀 CICDAutoDoc GitHub 통합 테스트")
        print(f"📋 {title}")
        print("="*80)
        
    def main_menu(self):
        """메인 메뉴"""
        while True:
            self.print_header("메인 메뉴")
            
            if self.access_token:
                print(f"✅ 로그인 상태: 인증됨")
            else:
                print(f"❌ 로그인 상태: 미인증")
                
            if self.selected_repo:
                print(f"📂 선택된 저장소: {self.selected_repo['full_name']}")
            
            print(f"\n메뉴를 선택하세요:")
            print(f"1. 🔐 GitHub OAuth 로그인")
            print(f"2. 📦 저장소 목록 조회")
            print(f"3. 🔗 웹훅 관리")
            print(f"4. 🧪 웹훅 이벤트 테스트")
            print(f"5. 🗃️  데이터베이스 상태 확인")
            print(f"6. 🚪 종료")
            
            choice = input(f"\n선택 (1-6): ").strip()
            
            if choice == "1":
                self.oauth_login()
            elif choice == "2":
                self.list_repositories()
            elif choice == "3":
                self.webhook_management()
            elif choice == "4":
                self.test_webhook_events()
            elif choice == "5":
                self.check_database()
            elif choice == "6":
                print(f"👋 테스트를 종료합니다.")
                break
            else:
                print(f"❌ 잘못된 선택입니다.")
                input(f"Enter를 눌러 계속...")
    
    def oauth_login(self):
        """GitHub OAuth 로그인"""
        self.print_header("GitHub OAuth 로그인")
        
        print(f"🔐 1단계: GitHub 인증 페이지 열기")
        login_url = f"{self.base_url}/github/auth/login"
        
        print(f"브라우저에서 GitHub 로그인 페이지를 열까요?")
        print(f"URL: {login_url}")
        
        open_browser = input(f"브라우저 열기? (y/N): ").strip().lower()
        
        if open_browser == 'y':
            try:
                webbrowser.open(login_url)
                print(f"✅ 브라우저가 열렸습니다!")
            except:
                print(f"⚠️  브라우저를 자동으로 열 수 없습니다. 수동으로 URL을 방문하세요.")
        
        print(f"\n🔐 2단계: Access Token 입력")
        print(f"GitHub 인증 완료 후 콜백 응답에서 'access_token'을 복사하세요.")
        
        self.access_token = input(f"Access Token: ").strip()
        
        if self.access_token:
            # 토큰 유효성 검증
            if self.validate_token():
                print(f"✅ 로그인 성공!")
                input(f"Enter를 눌러 계속...")
            else:
                print(f"❌ 토큰이 유효하지 않습니다.")
                self.access_token = None
                input(f"Enter를 눌러 계속...")
        else:
            print(f"❌ 토큰이 입력되지 않았습니다.")
            input(f"Enter를 눌러 계속...")
    
    def validate_token(self):
        """토큰 유효성 검증"""
        try:
            # GitHub API로 사용자 정보 조회 테스트
            response = requests.get(
                f"https://api.github.com/user",
                headers={"Authorization": f"token {self.access_token}"}
            )
            
            if response.status_code == 200:
                user_data = response.json()
                print(f"👤 사용자: {user_data.get('login')} ({user_data.get('name', 'N/A')})")
                return True
            else:
                return False
                
        except Exception as e:
            print(f"토큰 검증 실패: {e}")
            return False
    
    def list_repositories(self):
        """저장소 목록 조회"""
        self.print_header("저장소 목록 조회")
        
        if not self.access_token:
            print(f"❌ 먼저 로그인이 필요합니다.")
            input(f"Enter를 눌러 계속...")
            return
        
        print(f"📦 저장소 목록을 조회 중...")
        
        try:
            # GET /github/repositories API 호출
            response = requests.get(
                f"{self.base_url}/github/repositories",
                params={"access_token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                repositories = data.get("repositories", [])
                
                print(f"✅ 총 {len(repositories)}개의 저장소 (admin 권한):")
                
                if not repositories:
                    print(f"⚠️  admin 권한이 있는 저장소가 없습니다.")
                    input(f"Enter를 눌러 계속...")
                    return
                
                # 저장소 목록 출력
                for i, repo in enumerate(repositories, 1):
                    privacy = "🔒 Private" if repo['private'] else "🔓 Public"
                    print(f"{i:2d}. 📂 {repo['full_name']} ({privacy})")
                    print(f"     브랜치: {repo['default_branch']}")
                
                # 저장소 선택
                print(f"\n저장소를 선택하시겠습니까?")
                choice = input(f"저장소 번호 (1-{len(repositories)}) 또는 Enter로 건너뛰기: ").strip()
                
                if choice.isdigit() and 1 <= int(choice) <= len(repositories):
                    self.selected_repo = repositories[int(choice) - 1]
                    print(f"✅ '{self.selected_repo['full_name']}' 선택됨")
                
            else:
                print(f"❌ 저장소 조회 실패: {response.status_code}")
                try:
                    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
                except:
                    print(response.text)
                    
        except Exception as e:
            print(f"❌ API 호출 실패: {e}")
        
        input(f"Enter를 눌러 계속...")
    
    def webhook_management(self):
        """웹훅 관리"""
        while True:
            self.print_header("웹훅 관리")
            
            if not self.access_token:
                print(f"❌ 먼저 로그인이 필요합니다.")
                input(f"Enter를 눌러 계속...")
                return
                
            if self.selected_repo:
                print(f"📂 대상 저장소: {self.selected_repo['full_name']}")
            else:
                print(f"⚠️  저장소가 선택되지 않았습니다.")
            
            print(f"\n웹훅 관리 메뉴:")
            print(f"1. 🔗 현재 웹훅 목록 조회")
            print(f"2. ➕ 새 웹훅 등록")
            print(f"3. ❌ 웹훅 삭제")
            print(f"4. 📂 다른 저장소 선택")
            print(f"5. 🔙 메인 메뉴로 돌아가기")
            
            choice = input(f"\n선택 (1-5): ").strip()
            
            if choice == "1":
                self.list_webhooks()
            elif choice == "2":
                self.setup_webhook()
            elif choice == "3":
                self.delete_webhook()
            elif choice == "4":
                self.list_repositories()
            elif choice == "5":
                break
            else:
                print(f"❌ 잘못된 선택입니다.")
                input(f"Enter를 눌러 계속...")
    
    def list_webhooks(self):
        """웹훅 목록 조회"""
        self.print_header("웹훅 목록 조회")
        
        if not self.selected_repo:
            print(f"❌ 먼저 저장소를 선택해주세요.")
            input(f"Enter를 눌러 계속...")
            return
        
        owner, name = self.selected_repo['full_name'].split('/')
        
        print(f"🔗 {self.selected_repo['full_name']} 웹훅 조회 중...")
        
        try:
            # GET /github/webhooks/{repo_owner}/{repo_name} API 호출
            response = requests.get(
                f"{self.base_url}/github/webhooks/{owner}/{name}",
                params={"access_token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                self.current_webhooks = data.get("webhooks", [])
                
                print(f"✅ 웹훅 {len(self.current_webhooks)}개 발견:")
                
                if not self.current_webhooks:
                    print(f"  이 저장소에는 웹훅이 설정되어 있지 않습니다.")
                else:
                    for i, webhook in enumerate(self.current_webhooks, 1):
                        status = "🟢 활성" if webhook.get('active') else "🔴 비활성"
                        print(f"\n{i}. 🪝 웹훅 ID: {webhook.get('id')}")
                        print(f"   이름: {webhook.get('name')}")
                        print(f"   URL: {webhook.get('config', {}).get('url', 'N/A')}")
                        print(f"   이벤트: {', '.join(webhook.get('events', []))}")
                        print(f"   상태: {status}")
                        
            else:
                print(f"❌ 웹훅 조회 실패: {response.status_code}")
                print(response.text)
                
        except Exception as e:
            print(f"❌ API 호출 실패: {e}")
        
        input(f"Enter를 눌러 계속...")
    
    def setup_webhook(self):
        """웹훅 등록"""
        self.print_header("웹훅 등록")
        
        if not self.selected_repo:
            print(f"❌ 먼저 저장소를 선택해주세요.")
            input(f"Enter를 눌러 계속...")
            return
        
        owner, name = self.selected_repo['full_name'].split('/')
        
        print(f"📂 저장소: {self.selected_repo['full_name']}")
        print(f"🔗 새 웹훅을 등록합니다.")
        
        # 웹훅 URL 입력
        default_url = "https://boilerless-thecate-willow.ngrok-free.dev"
        webhook_url = input(f"웹훅 URL (기본: {default_url}): ").strip() or default_url
        
        print(f"\\n🔧 웹훅 등록 중...")
        print(f"저장소: {owner}/{name}")
        print(f"웹훅 URL: {webhook_url}")
        
        try:
            # POST /github/setup-webhook API 호출
            response = requests.post(
                f"{self.base_url}/github/setup-webhook",
                params={
                    "repo_owner": owner,
                    "repo_name": name,
                    "access_token": self.access_token,
                    "webhook_url": webhook_url
                }
            )
            
            print(f"\\n📊 API 응답 (상태코드: {response.status_code}):")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ 웹훅 등록 성공!")
                print(f"웹훅 ID: {result.get('webhook', 'N/A')}")
                print(f"웹훅 URL: {result.get('webhook_url', 'N/A')}")
                
                # 데이터베이스 확인
                self.check_webhook_registration()
                
            else:
                print(f"❌ 웹훅 등록 실패:")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2, ensure_ascii=False))
                except:
                    print(response.text)
                    
        except Exception as e:
            print(f"❌ API 호출 실패: {e}")
        
        input(f"Enter를 눌러 계속...")
    
    def delete_webhook(self):
        """웹훅 삭제"""
        self.print_header("웹훅 삭제")
        
        if not self.selected_repo:
            print(f"❌ 먼저 저장소를 선택해주세요.")
            input(f"Enter를 눌러 계속...")
            return
        
        # 현재 웹훅 목록 다시 조회
        owner, name = self.selected_repo['full_name'].split('/')
        
        try:
            response = requests.get(
                f"{self.base_url}/github/webhooks/{owner}/{name}",
                params={"access_token": self.access_token}
            )
            
            if response.status_code == 200:
                data = response.json()
                webhooks = data.get("webhooks", [])
                
                if not webhooks:
                    print(f"삭제할 웹훅이 없습니다.")
                    input(f"Enter를 눌러 계속...")
                    return
                
                print(f"삭제할 웹훅을 선택하세요:")
                for i, webhook in enumerate(webhooks, 1):
                    print(f"{i}. 웹훅 ID: {webhook.get('id')} | URL: {webhook.get('config', {}).get('url', 'N/A')}")
                
                choice = input(f"선택 (1-{len(webhooks)}): ").strip()
                
                if choice.isdigit() and 1 <= int(choice) <= len(webhooks):
                    selected_webhook = webhooks[int(choice) - 1]
                    webhook_id = selected_webhook.get('id')
                    
                    confirm = input(f"웹훅 ID {webhook_id}를 정말 삭제하시겠습니까? (y/N): ").strip().lower()
                    
                    if confirm == 'y':
                        # DELETE /github/webhook/{webhook_id} API 호출
                        delete_response = requests.delete(
                            f"{self.base_url}/github/webhook/{webhook_id}",
                            params={
                                "repo_owner": owner,
                                "repo_name": name,
                                "access_token": self.access_token
                            }
                        )
                        
                        if delete_response.status_code == 200:
                            result = delete_response.json()
                            print(f"✅ 웹훅 삭제 성공!")
                            print(f"메시지: {result.get('message', 'N/A')}")
                        else:
                            print(f"❌ 웹훅 삭제 실패: {delete_response.status_code}")
                    else:
                        print(f"❌ 삭제가 취소되었습니다.")
                else:
                    print(f"❌ 잘못된 선택입니다.")
            else:
                print(f"❌ 웹훅 목록 조회 실패: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 오류: {e}")
        
        input(f"Enter를 눌러 계속...")
    
    def test_webhook_events(self):
        """웹훅 이벤트 테스트"""
        self.print_header("웹훅 이벤트 테스트")
        
        print(f"🧪 웹훅 엔드포인트 테스트")
        print(f"실제 GitHub에서 보내는 것과 같은 웹훅 이벤트를 시뮬레이션합니다.")
        
        print(f"\\n테스트할 이벤트 타입을 선택하세요:")
        print(f"1. 🏓 Ping 이벤트 (웹훅 연결 테스트)")
        print(f"2. 🚀 Push 이벤트 (코드 푸시 시뮬레이션)")
        print(f"3. 🔀 Pull Request 이벤트")
        print(f"4. 🔙 돌아가기")
        
        choice = input(f"선택 (1-4): ").strip()
        
        if choice == "1":
            self.test_ping_event()
        elif choice == "2":
            self.test_push_event()
        elif choice == "3":
            self.test_pr_event()
        elif choice == "4":
            return
        else:
            print(f"❌ 잘못된 선택입니다.")
            input(f"Enter를 눌러 계속...")
    
    def test_ping_event(self):
        """Ping 이벤트 테스트"""
        print(f"\\n🏓 Ping 이벤트 테스트 중...")
        
        ping_payload = {
            "zen": "Non-blocking is better than blocking.",
            "hook_id": 12345,
            "hook": {
                "type": "Repository",
                "id": 12345,
                "name": "web",
                "active": True,
                "events": ["push", "pull_request"],
                "config": {
                    "content_type": "json",
                    "insecure_ssl": "0"
                }
            },
            "repository": {
                "id": 1,
                "name": "test-repo",
                "full_name": "test-owner/test-repo",
                "private": False,
                "default_branch": "main"
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/github/webhook",
                json=ping_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "ping",
                    "X-GitHub-Delivery": "12345-67890-test-ping"
                }
            )
            
            print(f"응답 코드: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Ping 이벤트 성공!")
                try:
                    result = response.json()
                    print(f"응답: {result}")
                except:
                    print(f"응답: {response.text}")
            else:
                print(f"❌ Ping 이벤트 실패: {response.text}")
                
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
        
        input(f"Enter를 눌러 계속...")
    
    def test_push_event(self):
        """Push 이벤트 테스트"""
        print(f"\\n🚀 Push 이벤트 테스트 중...")
        
        repo_name = self.selected_repo['full_name'] if self.selected_repo else "test-owner/test-repo"
        
        push_payload = {
            "ref": "refs/heads/main",
            "before": "0000000000000000000000000000000000000000",
            "after": "abc123def456789012345678901234567890abcd",
            "repository": {
                "id": 1,
                "name": repo_name.split('/')[-1],
                "full_name": repo_name,
                "private": False,
                "default_branch": "main"
            },
            "commits": [
                {
                    "id": "abc123def456789012345678901234567890abcd",
                    "message": "Test commit from CICDAutoDoc integration test",
                    "author": {
                        "name": "Test User",
                        "email": "test@example.com"
                    },
                    "timestamp": "2025-10-14T02:30:00Z",
                    "added": ["test_integration.py"],
                    "modified": ["README.md"],
                    "removed": []
                }
            ],
            "head_commit": {
                "id": "abc123def456789012345678901234567890abcd",
                "message": "Test commit from CICDAutoDoc integration test",
                "author": {
                    "name": "Test User",
                    "email": "test@example.com"
                },
                "timestamp": "2025-10-14T02:30:00Z"
            }
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/github/webhook",
                json=push_payload,
                headers={
                    "Content-Type": "application/json",
                    "X-GitHub-Event": "push",
                    "X-GitHub-Delivery": "12345-67890-test-push"
                }
            )
            
            print(f"응답 코드: {response.status_code}")
            if response.status_code == 200:
                print(f"✅ Push 이벤트 처리 성공!")
                try:
                    result = response.json()
                    print(f"메시지: {result.get('message', 'N/A')}")
                    print(f"저장소: {result.get('repository', 'N/A')}")
                    
                    # 데이터베이스 확인
                    print(f"\\n🗃️  데이터베이스 업데이트 확인 중...")
                    time.sleep(1)  # 처리 시간 대기
                    self.check_recent_changes()
                    
                except Exception as parse_error:
                    print(f"응답 파싱 오류: {parse_error}")
                    print(f"원본 응답: {response.text}")
            else:
                print(f"❌ Push 이벤트 실패: {response.text}")
                
        except Exception as e:
            print(f"❌ 테스트 실패: {e}")
        
        input(f"Enter를 눌러 계속...")
    
    def test_pr_event(self):
        """Pull Request 이벤트 테스트"""
        print(f"\\n🔀 Pull Request 이벤트는 아직 구현되지 않았습니다.")
        input(f"Enter를 눌러 계속...")
    
    def check_webhook_registration(self):
        """웹훅 등록 확인"""
        print(f"\\n🗃️  웹훅 등록 상태 확인:")
        
        try:
            import sqlite3
            conn = sqlite3.connect("cicd_autodoc.db")
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT repo_owner, repo_name, webhook_id, is_active, created_at
                FROM webhook_registrations
                WHERE is_active = 1
                ORDER BY created_at DESC
                LIMIT 3
            """)
            
            webhooks = cursor.fetchall()
            
            if webhooks:
                print(f"활성 웹훅 {len(webhooks)}개:")
                for webhook in webhooks:
                    print(f"  🟢 {webhook[0]}/{webhook[1]} (ID: {webhook[2]}) - {webhook[4]}")
            else:
                print(f"활성 웹훅이 없습니다.")
            
            conn.close()
            
        except Exception as e:
            print(f"데이터베이스 확인 실패: {e}")
    
    def check_recent_changes(self):
        """최근 코드 변경사항 확인"""
        try:
            import sqlite3
            conn = sqlite3.connect("cicd_autodoc.db")
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT commit_sha, commit_message, timestamp
                FROM code_changes
                ORDER BY timestamp DESC
                LIMIT 3
            """)
            
            changes = cursor.fetchall()
            
            if changes:
                print(f"최근 코드 변경 {len(changes)}개:")
                for change in changes:
                    print(f"  📝 {change[0][:8]}... - {change[1][:50]}...")
            else:
                print(f"코드 변경사항이 없습니다.")
            
            conn.close()
            
        except Exception as e:
            print(f"데이터베이스 확인 실패: {e}")
    
    def check_database(self):
        """데이터베이스 상태 확인"""
        self.print_header("데이터베이스 상태 확인")
        
        try:
            import sqlite3
            conn = sqlite3.connect("cicd_autodoc.db")
            cursor = conn.cursor()
            
            # 전체 통계
            tables = {
                "repositories": "저장소",
                "code_changes": "코드 변경",
                "file_changes": "파일 변경",
                "documents": "생성 문서",
                "webhook_registrations": "웹훅 등록"
            }
            
            print(f"📊 전체 데이터 통계:")
            for table, name in tables.items():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"  {name}: {count}개")
            
            # 최근 활동
            print(f"\\n🕒 최근 활동 (최근 5개):")
            cursor.execute("""
                SELECT commit_sha, commit_message, timestamp
                FROM code_changes
                ORDER BY timestamp DESC
                LIMIT 5
            """)
            
            recent_changes = cursor.fetchall()
            
            if recent_changes:
                for change in recent_changes:
                    print(f"  📝 {change[0][:8]}... - {change[1][:40]}... ({change[2]})")
            else:
                print(f"  최근 활동이 없습니다.")
            
            # 웹훅 상태
            print(f"\\n🔗 웹훅 등록 현황:")
            cursor.execute("""
                SELECT repo_owner, repo_name, webhook_id, is_active
                FROM webhook_registrations
            """)
            
            webhooks = cursor.fetchall()
            
            if webhooks:
                for webhook in webhooks:
                    status = "🟢 활성" if webhook[3] else "🔴 비활성"
                    print(f"  {status} {webhook[0]}/{webhook[1]} (ID: {webhook[2]})")
            else:
                print(f"  등록된 웹훅이 없습니다.")
            
            conn.close()
            
        except Exception as e:
            print(f"❌ 데이터베이스 확인 실패: {e}")
        
        input(f"Enter를 눌러 계속...")

def main():
    """메인 함수"""
    try:
        tester = CICDAutoDocTester()
        tester.main_menu()
    except KeyboardInterrupt:
        print(f"\\n\\n👋 사용자가 테스트를 중단했습니다.")
    except Exception as e:
        print(f"\\n\\n❌ 예상치 못한 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()