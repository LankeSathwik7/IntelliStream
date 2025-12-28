"""Wikipedia API service for fetching encyclopedia content."""

import logging
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class WikipediaService:
    """Search and fetch content from Wikipedia."""

    def __init__(self):
        self.base_url = "https://en.wikipedia.org/api/rest_v1"
        self.search_url = "https://en.wikipedia.org/w/api.php"
        # Wikipedia API requires a User-Agent header
        self.headers = {
            "User-Agent": "IntelliStream/1.0 (RAG Intelligence Platform; https://github.com/intellistream)"
        }

    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Search Wikipedia for articles matching the query.

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of search results with title, snippet, and page_id
        """
        params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": limit,
            "format": "json",
            "utf8": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
                response = await client.get(self.search_url, params=params)
                response.raise_for_status()
                data = response.json()

                results = []
                for item in data.get("query", {}).get("search", []):
                    results.append({
                        "title": item.get("title", ""),
                        "snippet": self._clean_snippet(item.get("snippet", "")),
                        "page_id": item.get("pageid"),
                        "word_count": item.get("wordcount", 0),
                        "url": f"https://en.wikipedia.org/wiki/{item.get('title', '').replace(' ', '_')}"
                    })

                return results

        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")
            return []

    async def get_summary(self, title: str) -> Optional[Dict]:
        """
        Get the summary of a Wikipedia article.

        Args:
            title: Article title

        Returns:
            Dict with title, extract, and url
        """
        # URL encode the title
        encoded_title = title.replace(" ", "_")

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
                response = await client.get(
                    f"{self.base_url}/page/summary/{encoded_title}"
                )
                response.raise_for_status()
                data = response.json()

                return {
                    "title": data.get("title", title),
                    "extract": data.get("extract", ""),
                    "description": data.get("description", ""),
                    "url": data.get("content_urls", {}).get("desktop", {}).get("page", ""),
                    "thumbnail": data.get("thumbnail", {}).get("source"),
                }

        except Exception as e:
            logger.error(f"Wikipedia summary error: {e}")
            return None

    async def get_full_content(self, title: str, max_chars: int = 5000) -> Optional[Dict]:
        """
        Get the full content of a Wikipedia article.

        Args:
            title: Article title
            max_chars: Maximum characters to return

        Returns:
            Dict with title, content, and sections
        """
        params = {
            "action": "query",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "exlimit": 1,
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0, headers=self.headers) as client:
                response = await client.get(self.search_url, params=params)
                response.raise_for_status()
                data = response.json()

                pages = data.get("query", {}).get("pages", {})
                for page_id, page_data in pages.items():
                    if page_id == "-1":
                        return None

                    content = page_data.get("extract", "")
                    if len(content) > max_chars:
                        content = content[:max_chars] + "..."

                    return {
                        "title": page_data.get("title", title),
                        "content": content,
                        "page_id": page_id,
                        "url": f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"
                    }

                return None

        except Exception as e:
            logger.error(f"Wikipedia content error: {e}")
            return None

    async def search_and_summarize(self, query: str, max_results: int = 3) -> List[Dict]:
        """
        Search Wikipedia and get summaries for top results.

        Args:
            query: Search query
            max_results: Maximum results to return with summaries

        Returns:
            List of articles with summaries
        """
        # First search
        search_results = await self.search(query, limit=max_results)

        # Get summaries for each result
        articles = []
        for result in search_results:
            summary = await self.get_summary(result["title"])
            if summary:
                articles.append({
                    "title": summary["title"],
                    "content": summary["extract"],
                    "description": summary.get("description", ""),
                    "url": summary["url"],
                    "source": "wikipedia",
                    "score": 0.8  # Base score for Wikipedia results
                })

        return articles

    def _clean_snippet(self, snippet: str) -> str:
        """Remove HTML tags from snippet."""
        import re
        clean = re.sub(r'<[^>]+>', '', snippet)
        return clean.strip()


# Singleton instance
wikipedia_service = WikipediaService()
