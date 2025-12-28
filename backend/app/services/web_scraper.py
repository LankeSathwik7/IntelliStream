"""Web scraping service for extracting content from URLs."""

from typing import Dict, Optional, List
import httpx
from bs4 import BeautifulSoup
import re
from urllib.parse import urlparse


class WebScraperService:
    """Scrape and extract content from web pages."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        self.max_content_length = 10000  # Max characters to extract

    async def scrape_url(
        self,
        url: str,
        extract_links: bool = False,
        max_length: Optional[int] = None
    ) -> Dict:
        """
        Scrape content from a URL.

        Args:
            url: The URL to scrape
            extract_links: Whether to extract links from the page
            max_length: Maximum content length (default: 10000)

        Returns:
            Dict with title, content, links, metadata
        """
        max_length = max_length or self.max_content_length

        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers=self.headers
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                # Parse HTML
                soup = BeautifulSoup(response.text, "lxml")

                # Extract title
                title = self._extract_title(soup)

                # Extract main content
                content = self._extract_content(soup, max_length)

                # Extract metadata
                metadata = self._extract_metadata(soup, url)

                result = {
                    "url": url,
                    "title": title,
                    "content": content,
                    "metadata": metadata,
                    "success": True,
                    "error": None
                }

                # Extract links if requested
                if extract_links:
                    result["links"] = self._extract_links(soup, url)

                return result

        except httpx.TimeoutException:
            return {
                "url": url,
                "title": None,
                "content": None,
                "success": False,
                "error": "Request timed out"
            }
        except httpx.HTTPStatusError as e:
            return {
                "url": url,
                "title": None,
                "content": None,
                "success": False,
                "error": f"HTTP error: {e.response.status_code}"
            }
        except Exception as e:
            return {
                "url": url,
                "title": None,
                "content": None,
                "success": False,
                "error": str(e)
            }

    def _extract_title(self, soup: BeautifulSoup) -> str:
        """Extract page title."""
        # Try various title sources
        if soup.title and soup.title.string:
            return soup.title.string.strip()

        # Try Open Graph title
        og_title = soup.find("meta", property="og:title")
        if og_title and og_title.get("content"):
            return og_title["content"].strip()

        # Try h1
        h1 = soup.find("h1")
        if h1:
            return h1.get_text(strip=True)

        return "Untitled"

    def _extract_content(self, soup: BeautifulSoup, max_length: int) -> str:
        """Extract main text content from page."""
        # Remove unwanted elements
        for element in soup(["script", "style", "nav", "header", "footer",
                           "aside", "form", "iframe", "noscript"]):
            element.decompose()

        # Try to find main content area
        main_content = (
            soup.find("article") or
            soup.find("main") or
            soup.find(class_=re.compile(r"(content|article|post|entry)", re.I)) or
            soup.find(id=re.compile(r"(content|article|post|entry)", re.I)) or
            soup.body
        )

        if not main_content:
            return ""

        # Get text
        text = main_content.get_text(separator=" ", strip=True)

        # Clean up whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # Truncate if needed
        if len(text) > max_length:
            text = text[:max_length] + "..."

        return text

    def _extract_metadata(self, soup: BeautifulSoup, url: str) -> Dict:
        """Extract page metadata."""
        metadata = {
            "domain": urlparse(url).netloc,
        }

        # Description
        desc = soup.find("meta", attrs={"name": "description"})
        if desc and desc.get("content"):
            metadata["description"] = desc["content"][:500]

        # Open Graph
        og_desc = soup.find("meta", property="og:description")
        if og_desc and og_desc.get("content"):
            metadata["og_description"] = og_desc["content"][:500]

        # Author
        author = soup.find("meta", attrs={"name": "author"})
        if author and author.get("content"):
            metadata["author"] = author["content"]

        # Published date
        for attr in ["article:published_time", "datePublished", "pubdate"]:
            date_meta = soup.find("meta", property=attr) or soup.find("meta", attrs={"name": attr})
            if date_meta and date_meta.get("content"):
                metadata["published_date"] = date_meta["content"]
                break

        return metadata

    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[Dict]:
        """Extract links from the page."""
        links = []
        base_domain = urlparse(base_url).netloc

        for a in soup.find_all("a", href=True):
            href = a["href"]
            text = a.get_text(strip=True)

            # Skip empty or anchor links
            if not href or href.startswith("#") or href.startswith("javascript:"):
                continue

            # Make absolute URL
            if href.startswith("/"):
                href = f"https://{base_domain}{href}"
            elif not href.startswith("http"):
                continue

            # Skip if no text
            if not text:
                continue

            links.append({
                "url": href,
                "text": text[:100],
                "is_external": urlparse(href).netloc != base_domain
            })

        # Deduplicate and limit
        seen = set()
        unique_links = []
        for link in links:
            if link["url"] not in seen:
                seen.add(link["url"])
                unique_links.append(link)
                if len(unique_links) >= 20:
                    break

        return unique_links

    async def scrape_multiple(
        self,
        urls: List[str],
        max_per_page: int = 2000
    ) -> List[Dict]:
        """Scrape multiple URLs concurrently."""
        import asyncio

        tasks = [
            self.scrape_url(url, max_length=max_per_page)
            for url in urls[:10]  # Limit to 10 URLs
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        return [
            r if isinstance(r, dict) else {"url": urls[i], "success": False, "error": str(r)}
            for i, r in enumerate(results)
        ]


# Singleton instance
web_scraper_service = WebScraperService()
