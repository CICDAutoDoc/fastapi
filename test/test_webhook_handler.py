"""
Tests for webhook handler functionality
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
import json
from fastapi import Request
from domain.user.webhook_handler import WebhookHandler, handle_push_event, extract_code_changes
from domain.user.schemas import WebhookEventResponse
from models import CodeChange, Repository, User


class TestWebhookHandler:
    """Test webhook processing functionality."""
    
    def test_webhook_handler_init(self):
        """Test WebhookHandler initialization."""
        handler = WebhookHandler()
        
        assert handler.webhook_secret is not None
        assert hasattr(handler, 'verify_webhook_signature')
        assert hasattr(handler, 'handle_webhook')
    
    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification with valid signature."""
        handler = WebhookHandler()
        handler.webhook_secret = "test_secret"
        
        payload = b'{"test": "data"}'
        
        # Generate valid signature
        import hmac
        import hashlib
        mac = hmac.new(handler.webhook_secret.encode(), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"
        
        result = handler.verify_webhook_signature(payload, signature)
        assert result is True
    
    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature."""
        handler = WebhookHandler()
        handler.webhook_secret = "test_secret"
        
        payload = b'{"test": "data"}'
        invalid_signature = "sha256=invalid_signature"
        
        result = handler.verify_webhook_signature(payload, invalid_signature)
        assert result is False
    
    def test_verify_webhook_signature_no_signature(self):
        """Test webhook signature verification with no signature."""
        handler = WebhookHandler()
        
        payload = b'{"test": "data"}'
        
        result = handler.verify_webhook_signature(payload, None)
        assert result is False
    
    @pytest.mark.asyncio
    async def test_handle_webhook_unsupported_event(self):
        """Test handling of unsupported webhook event."""
        handler = WebhookHandler()
        handler.webhook_secret = "test_secret"
        
        # Mock request
        mock_request = Mock(spec=Request)
        payload = b'{"repository": {"full_name": "test/repo"}}'
        mock_request.body = AsyncMock(return_value=payload)
        mock_request.json = AsyncMock(return_value={"repository": {"full_name": "test/repo"}})
        
        # Generate valid signature
        import hmac
        import hashlib
        mac = hmac.new(handler.webhook_secret.encode(), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"
        
        result = await handler.handle_webhook(
            request=mock_request,
            x_github_event="issues",
            x_hub_signature_256=signature,
            x_github_delivery="test-delivery-123"
        )
        
        assert isinstance(result, WebhookEventResponse)
        assert result.success is True
        assert result.processed is False
        assert result.event_type == "issues"
        assert "received but not processed" in result.message

class TestPushEventHandler:
    """Test push event handler functions."""
    
    @pytest.mark.asyncio
    async def test_handle_push_event_main_branch(self, sample_webhook_payload):
        """Test push event handling for main branch."""
        with patch('domain.user.webhook_handler.extract_code_changes') as mock_extract, \
             patch('domain.user.webhook_handler.save_code_changes') as mock_save:
            
            mock_extract.return_value = {
                "total_changes": 5,
                "code_files": ["test.py", "main.py"]
            }
            
            result = await handle_push_event(sample_webhook_payload)
            
            assert "Extracted code changes from" in result["message"]
            assert result["repository"] == "testuser/test-repo"
            assert "changes" in result
    
    @pytest.mark.asyncio
    async def test_handle_push_event_non_main_branch(self):
        """Test push event handling for non-main branch."""
        payload = {
            "ref": "refs/heads/feature-branch",
            "repository": {
                "full_name": "testuser/test-repo",
                "default_branch": "main"
            },
            "commits": []
        }
        
        result = await handle_push_event(payload)
        
        assert "Not main branch, ignored" in result["message"]
    
    @pytest.mark.asyncio
    async def test_handle_push_event_no_code_changes(self):
        """Test push event with no meaningful code changes."""
        payload = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "testuser/test-repo",
                "default_branch": "main"
            },
            "commits": []
        }
        
        with patch('domain.user.webhook_handler.extract_code_changes') as mock_extract:
            mock_extract.return_value = None
            
            result = await handle_push_event(payload)
            
            assert "Extracted code changes from 0 commits" in result["message"]


class TestExtractCodeChanges:
    """Test code change extraction functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_code_changes_success(self):
        """Test successful code change extraction."""
        commit = {
            "id": "abc123def456",
            "message": "Add new feature"
        }
        
        repo_info = {
            "full_name": "testuser/test-repo"
        }
        
        mock_response_data = {
            "files": [
                {
                    "filename": "src/main.py",
                    "status": "modified",
                    "changes": 10,
                    "additions": 7,
                    "deletions": 3
                },
                {
                    "filename": "README.md",
                    "status": "modified", 
                    "changes": 2,
                    "additions": 2,
                    "deletions": 0
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await extract_code_changes(commit, repo_info)
            
            # Should only include Python file, not README
            assert result is not None
            assert len(result["code_files"]) == 1
            assert result["code_files"][0]["filename"] == "src/main.py"
            assert result["total_changes"] == 10
    
    @pytest.mark.asyncio
    async def test_extract_code_changes_api_error(self):
        """Test code change extraction with API error."""
        commit = {
            "id": "abc123def456",
            "message": "Add new feature"
        }
        
        repo_info = {
            "full_name": "testuser/test-repo"
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await extract_code_changes(commit, repo_info)
            
            assert result is None
    
    @pytest.mark.asyncio 
    async def test_extract_code_changes_no_code_files(self):
        """Test code change extraction with no code files."""
        commit = {
            "id": "abc123def456",
            "message": "Update documentation"
        }
        
        repo_info = {
            "full_name": "testuser/test-repo"
        }
        
        mock_response_data = {
            "files": [
                {
                    "filename": "README.md",
                    "status": "modified",
                    "changes": 5,
                    "additions": 3,
                    "deletions": 2
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = mock_response_data
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await extract_code_changes(commit, repo_info)
            
            # Should return None since no code files were changed
            assert result is None


class TestWebhookIntegration:
    """Integration tests for webhook processing."""
    
    @pytest.mark.asyncio
    async def test_handle_webhook_with_valid_signature(self):
        """Test complete webhook handling with valid signature."""
        handler = WebhookHandler()
        handler.webhook_secret = "test_secret"
        
        payload_data = {
            "ref": "refs/heads/main",
            "repository": {
                "full_name": "testuser/test-repo",
                "default_branch": "main"
            },
            "commits": []
        }
        
        payload = json.dumps(payload_data).encode()
        
        # Generate valid signature
        import hmac
        import hashlib
        mac = hmac.new(handler.webhook_secret.encode(), msg=payload, digestmod=hashlib.sha256)
        signature = f"sha256={mac.hexdigest()}"
        
        # Mock request
        mock_request = Mock(spec=Request)
        mock_request.body = AsyncMock(return_value=payload)
        mock_request.json = AsyncMock(return_value=payload_data)
        
        with patch('domain.user.webhook_handler.handle_push_event') as mock_handle_push:
            mock_handle_push.return_value = {
                "message": "Test push handled successfully",
                "repository": "testuser/test-repo",
                "changes": []
            }
            
            result = await handler.handle_webhook(
                request=mock_request,
                x_github_event="push",
                x_hub_signature_256=signature,
                x_github_delivery="test-delivery"
            )
            
            assert isinstance(result, WebhookEventResponse)
            assert result.success is True
            assert result.event_type == "push"
            assert result.processed is True
            assert mock_handle_push.called
    
    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(self):
        """Test webhook handling with invalid signature."""
        handler = WebhookHandler()
        handler.webhook_secret = "test_secret"
        
        payload = b'{"test": "data"}'
        invalid_signature = "sha256=invalid_signature"
        
        mock_request = Mock(spec=Request)
        mock_request.body = AsyncMock(return_value=payload)
        
        with pytest.raises(Exception):  # Should raise HTTPException
            await handler.handle_webhook(
                request=mock_request,
                x_github_event="push",
                x_hub_signature_256=invalid_signature,
                x_github_delivery="test-delivery"
            )