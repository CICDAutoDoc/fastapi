"""
Tests for git router functionality - focused on actual implementation
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi import HTTPException
from fastapi.testclient import TestClient
from domain.user.git_router import router


class TestGitRouter:
    """Test git router endpoints based on actual implementation."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for router."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    def test_auth_login(self, test_client):
        """Test GitHub OAuth login redirect."""
        response = test_client.get("/github/auth/login", allow_redirects=False)
        
        assert response.status_code == 307  # Redirect response
        assert "github.com" in response.headers["location"]
    
    @patch('httpx.AsyncClient')
    def test_auth_callback_success(self, mock_client, test_client):
        """Test successful GitHub OAuth callback."""
        # Mock httpx client responses
        mock_token_response = Mock()
        mock_token_response.json.return_value = {"access_token": "test_token_123"}
        
        mock_user_response = Mock()
        mock_user_response.json.return_value = {
            "login": "testuser",
            "id": 12345,
            "email": "test@example.com"
        }
        
        mock_client_instance = Mock()
        mock_client_instance.post = AsyncMock(return_value=mock_token_response)
        mock_client_instance.get = AsyncMock(return_value=mock_user_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = test_client.get("/github/auth/callback?code=test_code_123")
        
        assert response.status_code == 200
        data = response.json()
        assert "GitHub User" in data
        assert data["GitHub User"]["login"] == "testuser"
    
    def test_auth_callback_no_code(self, test_client):
        """Test OAuth callback without authorization code."""
        response = test_client.get("/github/auth/callback")
        
        assert response.status_code == 422  # FastAPI validation error
    
    @patch('httpx.AsyncClient')
    def test_auth_callback_failed_token(self, mock_client, test_client):
        """Test OAuth callback with failed token exchange."""
        # Mock failed token response
        mock_token_response = Mock()
        mock_token_response.json.return_value = {"error": "invalid_grant"}
        
        mock_client_instance = Mock()
        mock_client_instance.post = AsyncMock(return_value=mock_token_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        response = test_client.get("/github/auth/callback?code=invalid_code")
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Github OAuth failed" in data["error"]
    
    @patch('httpx.AsyncClient')
    def test_setup_webhook_success(self, mock_client, test_client):
        """Test successful webhook setup."""
        # Mock successful webhook creation response
        mock_webhook_response = Mock()
        mock_webhook_response.status_code = 201
        mock_webhook_response.json.return_value = {
            "id": 12345,
            "url": "https://api.github.com/repos/testuser/test-repo/hooks/12345",
            "config": {
                "url": "https://example.com/webhook",
                "content_type": "json"
            },
            "events": ["push", "pull_request"],
            "active": True
        }
        
        mock_client_instance = Mock()
        mock_client_instance.post = AsyncMock(return_value=mock_webhook_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        webhook_data = {
            "repo_owner": "testuser",
            "repo_name": "test-repo", 
            "access_token": "test_token",
            "webhook_url": "https://example.com/webhook"
        }
        
        response = test_client.post("/github/setup-webhook", params=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "webhook_id" in data
        assert data["webhook_id"] == 12345
    
    @patch('httpx.AsyncClient')
    def test_setup_webhook_failed(self, mock_client, test_client):
        """Test failed webhook setup."""
        # Mock failed webhook creation response
        mock_webhook_response = Mock()
        mock_webhook_response.status_code = 404
        mock_webhook_response.json.return_value = {"message": "Not Found"}
        
        mock_client_instance = Mock()
        mock_client_instance.post = AsyncMock(return_value=mock_webhook_response)
        mock_client.return_value.__aenter__.return_value = mock_client_instance
        
        webhook_data = {
            "repo_owner": "testuser",
            "repo_name": "nonexistent-repo",
            "access_token": "test_token", 
            "webhook_url": "https://example.com/webhook"
        }
        
        response = test_client.post("/github/setup-webhook", params=webhook_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert "Failed to create webhook" in data["error"]
    
    @patch('domain.user.git_router.handle_push_event')
    def test_webhook_push_event(self, mock_handle_push, test_client):
        """Test webhook push event handling."""
        mock_handle_push.return_value = {
            "message": "Push event processed successfully",
            "repository": "testuser/test-repo",
            "changes": []
        }
        
        webhook_payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "testuser/test-repo",
                "default_branch": "main"
            },
            "commits": []
        }
        
        response = test_client.post(
            "/github/webhook/push",
            json=webhook_payload,
            headers={"X-GitHub-Event": "push"}
        )
        
        assert response.status_code == 200
        mock_handle_push.assert_called_once_with(webhook_payload)
    
    @patch('domain.user.git_router.handle_pull_request_event')
    def test_webhook_pull_request_event(self, mock_handle_pr, test_client):
        """Test webhook pull request event handling."""
        mock_handle_pr.return_value = {
            "message": "Pull request event processed successfully",
            "repository": "testuser/test-repo"
        }
        
        webhook_payload = {
            "action": "opened",
            "pull_request": {
                "id": 123,
                "title": "Test PR"
            },
            "repository": {
                "full_name": "testuser/test-repo"
            }
        }
        
        response = test_client.post(
            "/github/webhook/pull_request",
            json=webhook_payload,
            headers={"X-GitHub-Event": "pull_request"}
        )
        
        assert response.status_code == 200
        mock_handle_pr.assert_called_once_with(webhook_payload)


class TestWebhookIntegration:
    """Test webhook integration functionality."""
    
    @pytest.fixture
    def test_client(self):
        """Create test client for router."""
        from fastapi import FastAPI
        app = FastAPI()
        app.include_router(router)
        return TestClient(app)
    
    @patch('domain.user.git_router.handle_push_event')
    @patch('domain.user.git_router.save_webhook_info')
    def test_complete_webhook_flow(self, mock_save_webhook, mock_handle_push, test_client):
        """Test complete webhook setup and processing flow."""
        # Mock webhook info saving
        mock_save_webhook.return_value = {"success": True}
        
        # Mock push event handling
        mock_handle_push.return_value = {
            "message": "Code changes processed successfully",
            "repository": "testuser/test-repo",
            "changes": [{"commit": "abc123", "files": ["test.py"]}]
        }
        
        # Simulate push event
        webhook_payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "testuser/test-repo",
                "default_branch": "main"
            },
            "commits": [{
                "id": "abc123",
                "message": "Test commit",
                "added": ["test.py"],
                "modified": [],
                "removed": []
            }]
        }
        
        response = test_client.post(
            "/github/webhook/push",
            json=webhook_payload
        )
        
        assert response.status_code == 200
        mock_handle_push.assert_called_once()
        
        # Verify the response structure
        data = response.json()
        assert "message" in data
        assert "repository" in data