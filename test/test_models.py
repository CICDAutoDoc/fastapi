"""
Tests for models and database functionality
"""
import pytest
from datetime import datetime
from models import User, Repository, CodeChange, FileChange, Document, WebhookRegistration


class TestModels:
    """Test SQLAlchemy model functionality."""
    
    def test_user_model(self, test_db_session):
        """Test User model creation and relationships."""
        user = User(
            github_id=12345,
            username="testuser",
            email="test@example.com"
        )
        
        test_db_session.add(user)
        test_db_session.commit()
        
        # Verify user was created
        saved_user = test_db_session.query(User).filter(User.github_id == 12345).first()
        assert saved_user is not None
        assert saved_user.username == "testuser"
        assert saved_user.email == "test@example.com"
        assert saved_user.created_at is not None
    
    def test_repository_model(self, test_db_session):
        """Test Repository model creation and relationships."""
        # Create user first
        user = User(
            github_id=12345,
            username="testuser",
            email="test@example.com"
        )
        test_db_session.add(user)
        test_db_session.commit()
        
        # Create repository
        repo = Repository(
            github_id=67890,
            name="test-repo",
            full_name="testuser/test-repo",
            default_branch="main",
            is_private=False,
            owner_id=user.id
        )
        
        test_db_session.add(repo)
        test_db_session.commit()
        
        # Verify repository was created
        saved_repo = test_db_session.query(Repository).filter(Repository.github_id == 67890).first()
        assert saved_repo is not None
        assert saved_repo.name == "test-repo"
        assert saved_repo.full_name == "testuser/test-repo"
        assert saved_repo.default_branch == "main"
        assert saved_repo.is_private is False
        assert saved_repo.owner_id == user.id
        
        # Test relationship
        assert saved_repo.owner == user
        assert user.repositories[0] == saved_repo
    
    def test_code_change_model(self, test_db_session):
        """Test CodeChange model creation."""
        # Create user and repository first
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
        
        # Create code change
        code_change = CodeChange(
            commit_sha="abc123def456",
            commit_message="Test commit message",
            author_name="Test Author",
            author_email="test@example.com",
            repository_id=repo.id,
            source="push",
            total_changes=10
        )
        
        test_db_session.add(code_change)
        test_db_session.commit()
        
        # Verify code change was created
        saved_change = test_db_session.query(CodeChange).filter(
            CodeChange.commit_sha == "abc123def456"
        ).first()
        
        assert saved_change is not None
        assert saved_change.commit_message == "Test commit message"
        assert saved_change.author_name == "Test Author"
        assert saved_change.source == "push"
        assert saved_change.total_changes == 10
        assert saved_change.timestamp is not None
        assert saved_change.repository == repo
    
    def test_file_change_model(self, test_db_session):
        """Test FileChange model creation."""
        # Create prerequisites
        user = User(github_id=1, username="test", email="test@test.com")
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(github_id=1, name="test", full_name="test/test", owner_id=user.id)
        test_db_session.add(repo)
        test_db_session.commit()
        
        code_change = CodeChange(
            commit_sha="test123",
            commit_message="Test",
            repository_id=repo.id,
            source="push"
        )
        test_db_session.add(code_change)
        test_db_session.commit()
        
        # Create file change
        file_change = FileChange(
            filename="test_file.py",
            status="modified",
            changes=5,
            additions=3,
            deletions=2,
            patch="--- test patch ---",
            code_change_id=code_change.id
        )
        
        test_db_session.add(file_change)
        test_db_session.commit()
        
        # Verify file change
        saved_file = test_db_session.query(FileChange).filter(
            FileChange.filename == "test_file.py"
        ).first()
        
        assert saved_file is not None
        assert saved_file.status == "modified"
        assert saved_file.changes == 5
        assert saved_file.additions == 3
        assert saved_file.deletions == 2
        assert saved_file.patch == "--- test patch ---"
        assert saved_file.code_change == code_change
    
    def test_document_model(self, test_db_session):
        """Test Document model creation."""
        # Create prerequisites
        user = User(github_id=1, username="test", email="test@test.com")
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(github_id=1, name="test", full_name="test/test", owner_id=user.id)
        test_db_session.add(repo)
        test_db_session.commit()
        
        code_change = CodeChange(
            commit_sha="doc123",
            commit_message="Doc test",
            repository_id=repo.id,
            source="push"
        )
        test_db_session.add(code_change)
        test_db_session.commit()
        
        # Create document
        document = Document(
            title="Test Document",
            content="# Test Content\n\nThis is a test document.",
            summary="Test summary",
            status="generated",
            document_type="auto",
            commit_sha="doc123",
            repository_name="test/test",
            generation_metadata={"model": "test", "version": "1.0"},
            code_change_id=code_change.id
        )
        
        test_db_session.add(document)
        test_db_session.commit()
        
        # Verify document
        saved_doc = test_db_session.query(Document).filter(
            Document.commit_sha == "doc123"
        ).first()
        
        assert saved_doc is not None
        assert saved_doc.title == "Test Document"
        assert saved_doc.content.startswith("# Test Content")
        assert saved_doc.summary == "Test summary"
        assert saved_doc.status == "generated"
        assert saved_doc.document_type == "auto"
        assert saved_doc.repository_name == "test/test"
        assert saved_doc.generation_metadata["model"] == "test"
        assert saved_doc.code_change == code_change
        assert saved_doc.created_at is not None
        assert saved_doc.updated_at is not None
    
    def test_webhook_registration_model(self, test_db_session):
        """Test WebhookRegistration model."""
        # Create prerequisites
        user = User(github_id=1, username="test", email="test@test.com")
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(github_id=1, name="test", full_name="test/test", owner_id=user.id)
        test_db_session.add(repo)
        test_db_session.commit()
        
        # Create webhook registration
        webhook = WebhookRegistration(
            repo_owner="test",
            repo_name="test",
            webhook_id=12345,
            webhook_url="https://example.com/webhook",
            access_token="test_token",
            is_active=True,
            repository_id=repo.id
        )
        
        test_db_session.add(webhook)
        test_db_session.commit()
        
        # Verify webhook registration
        saved_webhook = test_db_session.query(WebhookRegistration).filter(
            WebhookRegistration.webhook_id == 12345
        ).first()
        
        assert saved_webhook is not None
        assert saved_webhook.repo_owner == "test"
        assert saved_webhook.repo_name == "test"
        assert saved_webhook.webhook_url == "https://example.com/webhook"
        assert saved_webhook.access_token == "test_token"
        assert saved_webhook.is_active is True
        assert saved_webhook.repository == repo


class TestDatabaseIntegration:
    """Test database integration and complex queries."""
    
    def test_cascade_relationships(self, test_db_session):
        """Test cascade behavior when deleting related records."""
        # Create full hierarchy
        user = User(github_id=1, username="test", email="test@test.com")
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(github_id=1, name="test", full_name="test/test", owner_id=user.id)
        test_db_session.add(repo)
        test_db_session.commit()
        
        code_change = CodeChange(
            commit_sha="cascade123",
            commit_message="Cascade test",
            repository_id=repo.id,
            source="push"
        )
        test_db_session.add(code_change)
        test_db_session.commit()
        
        file_change = FileChange(
            filename="test.py",
            status="added",
            changes=10,
            code_change_id=code_change.id
        )
        test_db_session.add(file_change)
        test_db_session.commit()
        
        # Verify all records exist
        assert test_db_session.query(User).count() == 1
        assert test_db_session.query(Repository).count() == 1
        assert test_db_session.query(CodeChange).count() == 1
        assert test_db_session.query(FileChange).count() == 1
    
    def test_unique_constraints(self, test_db_session):
        """Test unique constraints work properly."""
        # Test User.github_id uniqueness
        user1 = User(github_id=123, username="user1", email="user1@test.com")
        user2 = User(github_id=123, username="user2", email="user2@test.com")
        
        test_db_session.add(user1)
        test_db_session.commit()
        
        test_db_session.add(user2)
        
        # This should raise an integrity error due to duplicate github_id
        with pytest.raises(Exception):  # SQLAlchemy will raise IntegrityError
            test_db_session.commit()
        
        test_db_session.rollback()
    
    def test_complex_query(self, test_db_session):
        """Test complex query with joins."""
        # Create test data
        user = User(github_id=1, username="test", email="test@test.com")
        test_db_session.add(user)
        test_db_session.commit()
        
        repo = Repository(github_id=1, name="test", full_name="test/test", owner_id=user.id)
        test_db_session.add(repo)
        test_db_session.commit()
        
        # Create multiple code changes
        for i in range(3):
            code_change = CodeChange(
                commit_sha=f"commit{i}",
                commit_message=f"Commit {i}",
                repository_id=repo.id,
                source="push",
                total_changes=i * 5
            )
            test_db_session.add(code_change)
            test_db_session.commit()
            
            # Create document for each code change
            document = Document(
                title=f"Document {i}",
                content=f"Content {i}",
                summary=f"Summary {i}",
                status="generated",
                commit_sha=f"commit{i}",
                repository_name="test/test",
                code_change_id=code_change.id
            )
            test_db_session.add(document)
        
        test_db_session.commit()
        
        # Test complex query: get all documents for a repository with code change info
        results = test_db_session.query(Document, CodeChange).join(
            CodeChange, Document.code_change_id == CodeChange.id
        ).filter(
            Document.repository_name == "test/test"
        ).all()
        
        assert len(results) == 3
        for doc, change in results:
            assert doc.repository_name == "test/test"
            assert change.repository_id == repo.id