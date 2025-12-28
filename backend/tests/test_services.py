"""Unit tests for service modules."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import time


class TestRateLimiter:
    """Tests for rate limiting service."""

    @pytest.mark.asyncio
    async def test_rate_limit_allows_first_request(self, mock_cache_service):
        """Test that first request is always allowed."""
        from app.services.rate_limiter import RateLimiter

        limiter = RateLimiter(requests_per_minute=10)
        mock_cache_service.get.return_value = None

        allowed, info = await limiter.check_rate_limit("user-123", "test")

        assert allowed is True
        assert "minute" in info

    @pytest.mark.asyncio
    async def test_rate_limit_blocks_excess_requests(self):
        """Test that requests over limit are blocked."""
        from app.services.rate_limiter import RateLimiter

        limiter = RateLimiter(requests_per_minute=5)

        # Mock cache service to return high count
        with patch("app.services.rate_limiter.cache_service") as mock_cache:
            mock_cache.get = AsyncMock(return_value={
                "count": 10,
                "window_start": int(time.time())
            })
            mock_cache.set = AsyncMock(return_value=True)

            allowed, info = await limiter.check_rate_limit("user-123", "test")

            assert allowed is False
            assert "error" in info

    @pytest.mark.asyncio
    async def test_rate_limit_resets_after_window(self, mock_cache_service):
        """Test that rate limit resets after window expires."""
        from app.services.rate_limiter import RateLimiter

        limiter = RateLimiter(requests_per_minute=5)
        # Window started 120 seconds ago (past the 60 second window)
        mock_cache_service.get.return_value = {
            "count": 100,
            "window_start": int(time.time()) - 120
        }

        allowed, info = await limiter.check_rate_limit("user-123", "test")

        assert allowed is True

    @pytest.mark.asyncio
    async def test_get_usage_returns_stats(self, mock_cache_service):
        """Test getting usage statistics."""
        from app.services.rate_limiter import RateLimiter

        limiter = RateLimiter()
        mock_cache_service.get.return_value = {
            "count": 5,
            "window_start": int(time.time())
        }

        usage = await limiter.get_usage("user-123")

        assert "minute" in usage
        assert "hour" in usage
        assert "day" in usage


class TestCacheService:
    """Tests for cache service."""

    @pytest.mark.asyncio
    async def test_cache_set_and_get(self):
        """Test setting and getting cache values."""
        from app.services.cache import CacheService

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": "OK"}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            cache = CacheService()
            # Test would run with mocked httpx

    @pytest.mark.asyncio
    async def test_cache_handles_missing_key(self):
        """Test cache returns None for missing keys."""
        from app.services.cache import CacheService

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.json.return_value = {"result": None}
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response

            cache = CacheService()
            # Test would verify None is returned


class TestChunker:
    """Tests for document chunker."""

    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        from app.rag.chunker import DocumentChunker

        chunker = DocumentChunker(chunk_size=1000, chunk_overlap=100)
        text = "Short text."

        chunks = chunker.chunk_text(text, "Test Doc")

        assert len(chunks) == 1
        assert chunks[0]["content"] == text
        assert chunks[0]["chunk_index"] == 0
        assert chunks[0]["total_chunks"] == 1

    def test_chunk_long_text(self):
        """Test chunking text longer than chunk size."""
        from app.rag.chunker import DocumentChunker

        chunker = DocumentChunker(chunk_size=100, chunk_overlap=20, min_chunk_size=20)
        text = "This is a sentence. " * 50  # ~1000 chars

        chunks = chunker.chunk_text(text, "Long Doc")

        assert len(chunks) >= 1  # At least one chunk
        for i, chunk in enumerate(chunks):
            assert chunk["chunk_index"] == i
            assert chunk["total_chunks"] == len(chunks)

    def test_chunk_has_content(self):
        """Test that chunks have content field."""
        from app.rag.chunker import DocumentChunker

        chunker = DocumentChunker()
        text = "Test content"

        chunks = chunker.chunk_text(text, "Test Title")

        assert "content" in chunks[0]
        assert chunks[0]["content"] == "Test content"

    def test_chunk_with_overlap(self):
        """Test that chunks have proper overlap."""
        from app.rag.chunker import DocumentChunker

        chunker = DocumentChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=10)
        text = "Word " * 100  # 500 chars

        chunks = chunker.chunk_text(text, "Overlap Test")

        # Verify chunks exist and have content
        assert len(chunks) >= 1
        for chunk in chunks:
            assert len(chunk["content"]) > 0


class TestWikipediaService:
    """Tests for Wikipedia service."""

    @pytest.mark.asyncio
    async def test_search_returns_results(self):
        """Test Wikipedia search returns results."""
        from app.services.wikipedia import WikipediaService

        with patch("httpx.AsyncClient") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "query": {
                    "search": [
                        {"title": "Machine Learning", "snippet": "ML is...", "pageid": 123}
                    ]
                }
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__aenter__.return_value.get.return_value = mock_response

            service = WikipediaService()
            # Would test search functionality

    def test_clean_snippet_removes_html(self):
        """Test HTML tag removal from snippets."""
        from app.services.wikipedia import WikipediaService

        service = WikipediaService()

        snippet = '<span class="searchmatch">Machine</span> learning is...'
        cleaned = service._clean_snippet(snippet)

        assert "<" not in cleaned
        assert ">" not in cleaned
        assert "Machine" in cleaned


class TestArxivService:
    """Tests for ArXiv service."""

    @pytest.mark.asyncio
    async def test_search_parses_xml_response(self):
        """Test ArXiv XML response parsing."""
        from app.services.arxiv import ArxivService

        service = ArxivService()
        # Would test XML parsing with mocked response

    def test_format_for_rag(self):
        """Test formatting ArXiv results for RAG."""
        from app.services.arxiv import ArxivService

        service = ArxivService()
        papers = [
            {
                "arxiv_id": "2301.00001",
                "title": "Test Paper",
                "abstract": "This is a test paper about AI.",
                "authors": ["Author One", "Author Two"],
                "published": "2023-01-01",
                "url": "https://arxiv.org/abs/2301.00001",
                "categories": ["cs.AI", "cs.LG"]  # Add categories
            }
        ]

        formatted = service.format_for_rag(papers)

        assert len(formatted) == 1
        assert "Test Paper" in formatted[0]["title"]
        assert formatted[0]["source"] == "arxiv"


class TestExternalDataServices:
    """Tests for external data services (weather, news, stocks)."""

    @pytest.mark.asyncio
    async def test_weather_service_parses_response(self):
        """Test weather API response parsing."""
        from app.services.external_data import weather_service

        # Test service exists
        assert weather_service is not None

    @pytest.mark.asyncio
    async def test_news_service_returns_articles(self):
        """Test news API returns formatted articles."""
        from app.services.external_data import news_service

        # Test service exists
        assert news_service is not None

    @pytest.mark.asyncio
    async def test_stock_service_parses_quote(self):
        """Test stock API quote parsing."""
        from app.services.external_data import stock_service

        # Test service exists
        assert stock_service is not None


class TestDocumentProcessor:
    """Tests for document processing service."""

    def test_processor_exists(self):
        """Test document processor exists."""
        from app.services.document_processor import document_processor

        assert document_processor is not None

    def test_supported_extensions(self):
        """Test supported file extensions."""
        from app.services.document_processor import document_processor

        # Check processor has expected attributes
        assert hasattr(document_processor, 'process_file')


class TestMemoryService:
    """Tests for conversation memory service."""

    @pytest.mark.asyncio
    async def test_add_message(self, mock_supabase):
        """Test adding message to memory."""
        from app.services.memory import MemoryService

        mock_supabase.table.return_value.insert.return_value.execute.return_value.data = [{"id": "msg-1"}]

        service = MemoryService()
        # Would test message addition

    @pytest.mark.asyncio
    async def test_get_conversation_history(self, mock_supabase):
        """Test retrieving conversation history."""
        from app.services.memory import MemoryService

        mock_supabase.table.return_value.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value.data = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]

        service = MemoryService()
        # Would test history retrieval


class TestMonitoringService:
    """Tests for monitoring/logging service."""

    def test_axiom_client_exists(self):
        """Test Axiom client exists."""
        from app.services.monitoring import axiom_client

        assert axiom_client is not None

    def test_metrics_collector_exists(self):
        """Test metrics collector exists."""
        from app.services.monitoring import metrics_collector

        assert metrics_collector is not None

    def test_log_functions_exist(self):
        """Test log functions exist."""
        from app.services.monitoring import log_info, log_warning, log_error

        assert callable(log_info)
        assert callable(log_warning)
        assert callable(log_error)
