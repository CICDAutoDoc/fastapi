"""
수동으로 설정한 웹훅 정보를 데이터베이스에 등록하는 도구
"""
import sqlite3
from datetime import datetime

def register_manual_webhook():
    """수동으로 설정한 웹훅 정보를 데이터베이스에 등록"""
    
    print("🔗 수동 웹훅 등록 도구")
    print("=" * 40)
    
    try:
        conn = sqlite3.connect("cicd_autodoc.db")
        cursor = conn.cursor()
        
        # 현재 웹훅 등록 현황 확인
        cursor.execute("SELECT COUNT(*) FROM webhook_registrations")
        current_count = cursor.fetchone()[0]
        print(f"현재 등록된 웹훅: {current_count}개")
        
        if current_count > 0:
            print("이미 웹훅이 등록되어 있습니다.")
            cursor.execute("SELECT repo_owner, repo_name, webhook_url FROM webhook_registrations")
            webhooks = cursor.fetchall()
            for webhook in webhooks:
                print(f"  - {webhook[0]}/{webhook[1]} → {webhook[2]}")
            
            response = input("새로 등록하시겠습니까? (y/N): ")
            if response.lower() != 'y':
                return
        
        # 웹훅 정보 입력
        print("\n웹훅 정보를 입력하세요:")
        repo_owner = input("저장소 소유자 (예: CICDAutoDoc): ") or "CICDAutoDoc"
        repo_name = input("저장소 이름 (예: fastapi): ") or "fastapi"
        webhook_url = input("웹훅 URL (예: https://xxx.ngrok-free.dev/github/webhook): ") or "https://boilerless-thecate-willow.ngrok-free.dev/github/webhook"
        webhook_id = input("웹훅 ID (GitHub에서 확인, 예: 12345): ") or "999999"  # 임시 ID
        
        # 데이터베이스에 등록
        cursor.execute("""
            INSERT INTO webhook_registrations 
            (repo_owner, repo_name, webhook_id, webhook_url, access_token, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            repo_owner,
            repo_name, 
            int(webhook_id),
            webhook_url,
            "manual_setup",  # 수동 설정 표시
            True,  # 활성화
            datetime.now().isoformat()
        ))
        
        conn.commit()
        
        print(f"\n✅ 웹훅 등록 완료!")
        print(f"   저장소: {repo_owner}/{repo_name}")
        print(f"   웹훅 URL: {webhook_url}")
        print(f"   웹훅 ID: {webhook_id}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ 웹훅 등록 실패: {e}")

if __name__ == "__main__":
    register_manual_webhook()