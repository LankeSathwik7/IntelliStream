"""Pytest configuration and shared fixtures."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing without real API keys."""
    with patch("app.config.settings") as mock:
        mock.supabase_url = "https://test.supabase.co"
        mock.supabase_anon_key = "test-anon-key"
        mock.supabase_service_role_key = "test-service-key"
        mock.groq_api_key = "test-groq-key"
        mock.voyage_api_key = "test-voyage-key"
        mock.upstash_redis_rest_url = "https://test.upstash.io"
        mock.upstash_redis_rest_token = "test-redis-token"
        mock.tavily_api_key = "test-tavily-key"
        mock.newsapi_key = "test-news-key"
        mock.openweather_api_key = "test-weather-key"
        mock.alphavantage_api_key = "test-stock-key"
        mock.environment = "test"
        mock.debug = True
        mock.is_configured = True
        mock.is_production = False
        yield mock


@pytest.fixture
def mock_supabase():
    """Mock Supabase client."""
    with patch("app.services.supabase.create_client") as mock:
        client = MagicMock()
        mock.return_value = client
        yield client


@pytest.fixture
def mock_cache_service():
    """Mock Redis cache service."""
    with patch("app.services.cache.cache_service") as mock:
        mock.get = AsyncMock(return_value=None)
        mock.set = AsyncMock(return_value=True)
        mock.delete = AsyncMock(return_value=True)
        yield mock


@pytest.fixture
def mock_llm_service():
    """Mock LLM service."""
    with patch("app.services.llm.llm_service") as mock:
        mock.generate = AsyncMock(return_value="Test response from LLM")
        mock.generate_structured = AsyncMock(return_value={"key": "value"})
        yield mock


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service."""
    with patch("app.rag.embeddings.embedding_service") as mock:
        mock.embed_text = AsyncMock(return_value=[0.1] * 1024)
        mock.embed_batch = AsyncMock(return_value=[[0.1] * 1024])
        yield mock


@pytest.fixture
def sample_documents():
    """Sample documents for testing."""
    return [
        {
            "id": "doc-1",
            "title": "Test Document 1",
            "content": "This is test content for document one about AI.",
            "source_url": "https://example.com/doc1",
            "score": 0.95
        },
        {
            "id": "doc-2",
            "title": "Test Document 2",
            "content": "This is test content for document two about machine learning.",
            "source_url": "https://example.com/doc2",
            "score": 0.85
        },
        {
            "id": "doc-3",
            "title": "Test Document 3",
            "content": "This is test content for document three about neural networks.",
            "source_url": "https://example.com/doc3",
            "score": 0.75
        }
    ]


@pytest.fixture
def sample_user():
    """Sample authenticated user."""
    return {
        "id": "user-123",
        "email": "test@example.com",
        "role": "authenticated",
        "created_at": "2024-01-01T00:00:00Z"
    }


@pytest.fixture
def sample_agent_state():
    """Sample agent state for testing."""
    return {
        "query": "What is machine learning?",
        "thread_id": "thread-123",
        "user_id": "user-123",
        "route_decision": "",
        "retrieved_documents": [],
        "context": "",
        "analysis": {},
        "synthesized_response": "",
        "final_response": "",
        "sources": [],
        "agent_trace": [],
        "total_latency_ms": 0,
    }


@pytest.fixture
def test_client():
    """FastAPI test client with mocked dependencies."""
    from app.main import app
    return TestClient(app)
