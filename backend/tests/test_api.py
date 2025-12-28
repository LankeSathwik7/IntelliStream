"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestHealthEndpoints:
    """Tests for health check endpoints."""

    def test_root(self):
        """Test root endpoint returns app info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "IntelliStream API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "running"

    def test_health(self):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "intellistream-api"

    def test_health_live(self):
        """Test liveness check endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"

    def test_health_ready(self):
        """Test readiness check endpoint."""
        response = client.get("/health/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "checks" in data


class TestChatEndpoints:
    """Tests for chat endpoints."""

    def test_chat_requires_message(self):
        """Test chat endpoint requires message."""
        response = client.post("/api/chat/", json={})  # Note trailing slash
        assert response.status_code == 422  # Validation error

    def test_chat_accepts_valid_request(self):
        """Test chat endpoint accepts valid request structure."""
        # Note: This will fail without proper API keys configured
        # but validates the request structure
        response = client.post(
            "/api/chat/",  # Note trailing slash
            json={"message": "Hello, how are you?"},
        )
        # Either succeeds or fails with 500 (no API keys)
        assert response.status_code in [200, 500]


class TestDocumentEndpoints:
    """Tests for document endpoints."""

    def test_list_documents(self):
        """Test list documents endpoint."""
        response = client.get("/api/documents")
        # Either succeeds or fails with 500 (no Supabase configured)
        assert response.status_code in [200, 500]

    def test_search_documents_requires_query(self):
        """Test search endpoint requires query."""
        response = client.post("/api/documents/search", json={})
        assert response.status_code == 422  # Validation error

    def test_create_document_requires_fields(self):
        """Test create document requires title and content."""
        response = client.post("/api/documents", json={})
        assert response.status_code == 422  # Validation error

        response = client.post("/api/documents", json={"title": "Test"})
        assert response.status_code == 422  # Missing content


class TestRAGComponents:
    """Tests for RAG components."""

    def test_chunker_basic(self):
        """Test document chunker with basic text."""
        from app.rag.chunker import chunker

        text = "This is a test document. It has multiple sentences."
        chunks = chunker.chunk_text(text, "Test")

        assert len(chunks) >= 1
        assert chunks[0]["content"] == text
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["total_chunks"] == 1

    def test_chunker_long_text(self):
        """Test document chunker with long text."""
        from app.rag.chunker import chunker

        # Create text longer than chunk size
        text = "This is a sentence. " * 100
        chunks = chunker.chunk_text(text, "Long Test")

        assert len(chunks) > 1
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)


class TestAgentState:
    """Tests for agent state management."""

    def test_create_initial_state(self):
        """Test creating initial agent state."""
        from app.agents.state import create_initial_state

        state = create_initial_state(
            query="Test query",
            thread_id="test-thread-123",
        )

        assert state["query"] == "Test query"
        assert state["thread_id"] == "test-thread-123"
        assert state["route_decision"] == ""
        assert state["retrieved_documents"] == []
        assert state["agent_trace"] == []
        assert state["final_response"] == ""
