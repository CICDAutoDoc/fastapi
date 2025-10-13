"""
Tests for document_service module
"""
import pytest
from datetime import datetime
from sqlalchemy.orm import Session
from domain.langgraph.document_service import DocumentService, get_document_service, reset_document_service
from models import CodeChange, FileChange, Document, Repository, User


class TestDocumentService:
    """Test DocumentService functionality."""
    
    def test_document_service_initialization_mock(self):
        """Test DocumentService initialization with mock generator."""
        service = DocumentService(use_mock=True)
        
        assert service.generator is not None
        # Mock generator should be MockDocumentGenerator
        assert service.generator.__class__.__name__ == "MockDocumentGenerator"
    
    def test_document_service_initialization_real(self):
        """Test DocumentService initialization with real generator."""
        service = DocumentService(use_mock=False)
        
        assert service.generator is not None
        # Real generator should be DocumentGenerator
        assert service.generator.__class__.__name__ == "DocumentGenerator"
    
    @pytest.mark.asyncio
    async def test_process_code_change_not_found(self, test_db_session):
        """Test processing non-existent code change."""
        service = DocumentService(use_mock=True)
        
        # Mock SessionLocal to return our test session
        from domain.langgraph import document_service
        original_session_local = document_service.SessionLocal
        document_service.SessionLocal = lambda: test_db_session
        
        try:
            result = await service.process_code_change(999)
            
            assert result["success"] is False
            assert "not found" in result["error"].lower()
        finally:
            document_service.SessionLocal = original_session_local
    
    @pytest.mark.asyncio 
    async def test_process_code_change_new_document(self, test_db_session, sample_code_change_data):
        """Test creating new document from code change."""
        service = DocumentService(use_mock=True)
        
        # Create test data
        user = User(
            github_id=12345,
            username="testuser",
            email="test@example.com"
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(
            github_id=67890,
            name="test-repo",
            full_name="testuser/test-repo",
            owner_id=user.id
        )
        test_db_session.add(repo)
        test_db_session.commit()
        
        code_change = CodeChange(
            commit_sha=sample_code_change_data["commit_sha"],
            commit_message=sample_code_change_data["commit_message"],
            author_name=sample_code_change_data["author_name"],
            author_email=sample_code_change_data["author_email"],
            repository_id=repo.id,
            source=sample_code_change_data["source"],
            total_changes=sample_code_change_data["total_changes"]
        )
        test_db_session.add(code_change)
        test_db_session.commit()
        
        # Get the ID after commit - we'll use a hardcoded value for testing
        # Since we're using autoincrement, the first insert should have ID = 1
        code_change_id = 1
        
        # Add file changes
        for file_data in sample_code_change_data["files"]:
            file_change = FileChange(
                filename=file_data["filename"],
                status=file_data["status"],
                changes=file_data["changes"],
                additions=file_data["additions"],
                deletions=file_data["deletions"],
                patch=file_data["patch"],
                code_change_id=code_change_id
            )
            test_db_session.add(file_change)
        test_db_session.commit()
        
        # Mock SessionLocal to return our test session
        from domain.langgraph import document_service
        original_session_local = document_service.SessionLocal
        document_service.SessionLocal = lambda: test_db_session
        
        try:
            result = await service.process_code_change(code_change_id)
            
            assert result["success"] is True
            assert result["action"] == "created"
            assert "document_id" in result
            assert result["title"] is not None
            assert result["summary"] is not None
            
            # Verify document was created in database
            document = test_db_session.query(Document).filter(
                Document.commit_sha == sample_code_change_data["commit_sha"]
            ).first()
            
            assert document is not None
            assert document.status == "generated"
            assert document.code_change_id == code_change.id
            
        finally:
            document_service.SessionLocal = original_session_local
    
    def test_prepare_code_input(self, test_db_session):
        """Test _prepare_code_input method."""
        service = DocumentService(use_mock=True)
        
        # Create test repository
        user = User(github_id=1, username="test", email="test@test.com")
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(
            github_id=1,
            name="test",
            full_name="test/test",
            owner_id=user.id
        )
        test_db_session.add(repo)
        test_db_session.commit()
        
        # Create test code change
        code_change = CodeChange(
            commit_sha="test123",
            commit_message="Test message",
            author_name="Test Author",
            author_email="test@example.com",
            repository_id=repo.id,
            source="push",
            total_changes=5,
            timestamp=datetime.utcnow()
        )
        test_db_session.add(code_change)
        test_db_session.commit()
        
        # Create file changes
        file_changes = [
            FileChange(
                filename="test.py",
                status="modified",
                changes=5,
                additions=3,
                deletions=2,
                patch="test patch",
                code_change_id=code_change.id
            )
        ]
        for fc in file_changes:
            test_db_session.add(fc)
        test_db_session.commit()
        
        # Test _prepare_code_input
        code_input = service._prepare_code_input(code_change, file_changes)
        
        assert code_input.commit_sha == "test123"
        assert code_input.commit_message == "Test message"
        assert code_input.author_name == "Test Author"
        assert code_input.repository_name == "test/test"
        assert code_input.total_changes == 5
        assert len(code_input.files) == 1
        assert code_input.files[0]["filename"] == "test.py"
        assert code_input.files[0]["status"] == "modified"
    
    def test_get_documents_empty(self, test_db_session):
        """Test getting documents from empty database."""
        service = DocumentService(use_mock=True)
        
        # Mock SessionLocal
        from domain.langgraph import document_service
        original_session_local = document_service.SessionLocal
        document_service.SessionLocal = lambda: test_db_session
        
        try:
            documents = service.get_documents()
            assert documents == []
        finally:
            document_service.SessionLocal = original_session_local
    
    def test_get_document_detail_not_found(self, test_db_session):
        """Test getting non-existent document detail."""
        service = DocumentService(use_mock=True)
        
        # Mock SessionLocal
        from domain.langgraph import document_service
        original_session_local = document_service.SessionLocal
        document_service.SessionLocal = lambda: test_db_session
        
        try:
            result = service.get_document_detail(999)
            assert result is None
        finally:
            document_service.SessionLocal = original_session_local


class TestDocumentServiceSingleton:
    """Test DocumentService singleton pattern."""
    
    def test_get_document_service_singleton(self):
        """Test singleton behavior."""
        service1 = get_document_service()
        service2 = get_document_service()
        
        assert service1 is service2
    
    def test_reset_document_service(self):
        """Test resetting singleton."""
        service1 = get_document_service()
        reset_document_service()
        service2 = get_document_service()
        
        assert service1 is not service2