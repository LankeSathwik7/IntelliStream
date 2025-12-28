"""Web search service using Tavily API."""

from typing import List, Dict, Optional
import httpx
from app.config import settings


class WebSearchService:
    """Search the web using Tavily API (1000 free searches/month)."""

    def __init__(self):
        self.api_url = "https://api.tavily.com/search"
        self.api_key = getattr(settings, 'tavily_api_key', None)

    def is_configured(self) -> bool:
        """Check if Tavily API key is configured."""
        return bool(self.api_key and len(self.api_key) > 10)

    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",  # "basic" or "advanced"
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> List[Dict]:
        """
        Search the web for information.

        Args:
            query: Search query
            max_results: Maximum number of results (default 5)
            search_depth: "basic" (faster) or "advanced" (more thorough)
            include_domains: Only search these domains
            exclude_domains: Exclude these domains

        Returns:
            List of search results with title, url, content, score
        """
        if not self.is_configured():
            # Return empty results if not configured
            return []

        payload = {
            "api_key": self.api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": True,
            "include_raw_content": False,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.api_url, json=payload)
                response.raise_for_status()
                data = response.json()

                results = []

                # Include the AI-generated answer if available
                if data.get("answer"):
                    results.append({
                        "title": "AI Summary",
                        "url": None,
                        "content": data["answer"],
                        "score": 1.0,
                        "is_summary": True
                    })

                # Add search results
                for result in data.get("results", []):
                    results.append({
                        "title": result.get("title", ""),
                        "url": result.get("url", ""),
                        "content": result.get("content", ""),
                        "score": result.get("score", 0),
                        "is_summary": False
                    })

                return results

        except Exception as e:
            print(f"Web search error: {e}")
            return []

    async def search_news(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict]:
        """Search for recent news articles."""
        news_domains = [
            "reuters.com", "bloomberg.com", "cnbc.com",
            "techcrunch.com", "theverge.com", "wired.com",
            "arstechnica.com", "bbc.com", "cnn.com"
        ]
        return await self.search(
            query=query,
            max_results=max_results,
            include_domains=news_domains
        )

    async def search_research(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict]:
        """Search for research and academic content."""
        research_domains = [
            "arxiv.org", "nature.com", "science.org",
            "scholar.google.com", "researchgate.net",
            "ieee.org", "acm.org"
        ]
        return await self.search(
            query=query,
            max_results=max_results,
            include_domains=research_domains
        )


# Singleton instance
web_search_service = WebSearchService()
