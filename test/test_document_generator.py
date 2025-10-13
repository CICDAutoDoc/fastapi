"""
Tests for document_generator module
"""
import pytest
import asyncio
from unittest.mock import patch
from datetime import datetime
from domain.langgraph.document_generator import (
    DocumentGenerator, 
    MockDocumentGenerator, 
    CodeChangeInput,
    DocumentState,
    get_document_generator
)


class TestCodeChangeInput:
    """Test CodeChangeInput dataclass."""
    
    def test_code_change_input_creation(self):
        """Test creating CodeChangeInput with valid data."""
        input_data = CodeChangeInput(
            commit_sha="abc123",
            commit_message="Test commit",
            author_name="Test Author",
            repository_name="test/repo",
            timestamp=datetime.now().isoformat(),
            files=[{"filename": "test.py", "status": "modified"}],
            total_changes=10
        )
        
        assert input_data.commit_sha == "abc123"
        assert input_data.commit_message == "Test commit"
        assert input_data.author_name == "Test Author"
        assert len(input_data.files) == 1
        assert input_data.total_changes == 10


class TestMockDocumentGenerator:
    """Test MockDocumentGenerator functionality."""
    
    @pytest.mark.asyncio
    async def test_mock_generator_basic_functionality(self):
        """Test basic mock document generation."""
        generator = MockDocumentGenerator()
        
        input_data = CodeChangeInput(
            commit_sha="test123",
            commit_message="Test commit message",
            author_name="Test Author",
            repository_name="test/repo",
            timestamp=datetime.now().isoformat(),
            files=[
                {
                    "filename": "test_file.py",
                    "status": "modified",
                    "changes": 5,
                    "additions": 3,
                    "deletions": 2,
                    "patch": "--- test patch ---"
                }
            ],
            total_changes=5
        )
        
        result = await generator.generate_document(input_data)
        
        # Verify result structure
        assert result["success"] is True
        assert "title" in result
        assert "content" in result
        assert "summary" in result
        assert "metadata" in result
        
        # Verify content
        assert "Test commit message" in result["title"]
        assert "test123" in result["content"]
        assert "Test Author" in result["content"]
        assert "test_file.py" in result["content"]
        
        # Verify metadata
        assert result["metadata"]["model"] == "mock"
        assert result["metadata"]["file_count"] == 1
        assert result["metadata"]["total_changes"] == 5
    
    @pytest.mark.asyncio
    async def test_mock_generator_multiple_files(self):
        """Test mock generator with multiple files."""
        generator = MockDocumentGenerator()
        
        input_data = CodeChangeInput(
            commit_sha="multi123",
            commit_message="Multiple file changes",
            author_name="Multi Author",
            repository_name="test/multi-repo",
            timestamp=datetime.now().isoformat(),
            files=[
                {"filename": "file1.py", "status": "added", "changes": 10, "additions": 10, "deletions": 0},
                {"filename": "file2.py", "status": "modified", "changes": 5, "additions": 3, "deletions": 2},
                {"filename": "file3.py", "status": "removed", "changes": 8, "additions": 0, "deletions": 8}
            ],
            total_changes=23
        )
        
        result = await generator.generate_document(input_data)
        
        assert result["success"] is True
        assert result["metadata"]["file_count"] == 3
        assert result["metadata"]["total_changes"] == 23
        
        # Check all files are mentioned in content
        for file_info in input_data.files:
            assert file_info["filename"] in result["content"]


class TestDocumentGenerator:
    """Test DocumentGenerator (LLM-based) functionality."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_document_generator_initialization(self):
        """Test DocumentGenerator initialization with mocked API key."""
        generator = DocumentGenerator()
        
        assert generator.llm is not None
        assert generator.parser is not None
        assert generator.workflow is not None
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_document_generator_with_api_key(self):
        """Test DocumentGenerator initialization with API key."""
        generator = DocumentGenerator(openai_api_key="test-key")
        
        assert generator.llm is not None
        assert generator.parser is not None
        assert generator.workflow is not None
    
    @pytest.mark.asyncio
    async def test_document_generator_without_llm(self):
        """Test document generation without actual LLM (should handle gracefully)."""
        generator = DocumentGenerator(openai_api_key="invalid-key")
        
        input_data = CodeChangeInput(
            commit_sha="test456",
            commit_message="Test without LLM",
            author_name="Test Author",
            repository_name="test/repo",
            timestamp=datetime.now().isoformat(),
            files=[{"filename": "test.py", "status": "modified", "changes": 1, "additions": 1, "deletions": 0}],
            total_changes=1
        )
        
        # This should return an error result since we don't have valid OpenAI API key
        result = await generator.generate_document(input_data)
        
        # Should still return a structured response
        assert "success" in result
        assert "title" in result
        assert "content" in result
        assert "summary" in result
        assert "metadata" in result
        
        # But success should be False due to LLM failure
        if not result["success"]:
            assert "error" in result
            assert result["title"].startswith("문서 생성 실패")


class TestSingletonPattern:
    """Test singleton pattern for DocumentGenerator."""
    
    @patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'})
    def test_get_document_generator_singleton(self):
        """Test that get_document_generator returns the same instance."""
        gen1 = get_document_generator()
        gen2 = get_document_generator()
        
        assert gen1 is gen2
    
    def test_get_document_generator_with_different_keys(self):
        """Test singleton behavior with different API keys."""
        # First call creates instance
        gen1 = get_document_generator("key1")
        
        # Second call should return same instance (ignores new key)
        gen2 = get_document_generator("key2")
        
        assert gen1 is gen2


class TestDocumentState:
    """Test DocumentState TypedDict."""
    
    def test_document_state_structure(self):
        """Test DocumentState can be created and accessed."""
        input_data = CodeChangeInput(
            commit_sha="state123",
            commit_message="State test",
            author_name="State Author", 
            repository_name="state/repo",
            timestamp=datetime.now().isoformat(),
            files=[],
            total_changes=0
        )
        
        state = DocumentState(
            code_input=input_data,
            analysis_result="Test analysis",
            document_content="# Test Document",
            summary="Test summary",
            metadata={"test": "value"},
            messages=[]
        )
        
        assert state["code_input"] == input_data
        assert state["analysis_result"] == "Test analysis"
        assert state["document_content"] == "# Test Document"
        assert state["summary"] == "Test summary"
        assert state["metadata"]["test"] == "value"
        assert state["messages"] == []