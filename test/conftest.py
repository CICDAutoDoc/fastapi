"""
Test configuration and fixtures
"""
import pytest
import asyncio
import tempfile
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import Base
from models import *
from domain.langgraph.document_service import reset_document_service


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_db_session():
    """Create a test database session."""
    # Create temporary database
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()
    
    engine = create_engine(f"sqlite:///{temp_db.name}")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create session
    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = TestSessionLocal()
    
    try:
        yield session
    finally:
        session.close()
        os.unlink(temp_db.name)


@pytest.fixture
def sample_code_change_data():
    """Sample data for CodeChange testing."""
    return {
        "commit_sha": "abc123def456",
        "commit_message": "Add new feature",
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "source": "push",
        "total_changes": 10,
        "files": [
            {
                "filename": "test_file.py",
                "status": "modified",
                "changes": 5,
                "additions": 3,
                "deletions": 2,
                "patch": "--- a/test_file.py\n+++ b/test_file.py\n@@ -1,3 +1,4 @@\n def test():\n+    print('hello')\n     pass"
            }
        ]
    }


@pytest.fixture
def sample_webhook_payload():
    """Sample GitHub webhook payload."""
    return {
        "ref": "refs/heads/main",
        "commits": [
            {
                "id": "abc123def456",
                "message": "Add new feature",
                "author": {
                    "name": "Test Author",
                    "email": "test@example.com"
                },
                "modified": ["test_file.py"],
                "added": [],
                "removed": []
            }
        ],
        "repository": {
            "name": "test-repo",
            "full_name": "testuser/test-repo"
        }
    }


@pytest.fixture(autouse=True)
def reset_services():
    """Reset singleton services before each test."""
    reset_document_service()
    yield
    reset_document_service()