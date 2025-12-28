"""ArXiv API service for fetching research papers."""

import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Optional
from datetime import datetime


class ArxivService:
    """Search and fetch research papers from ArXiv."""

    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.namespaces = {
            "atom": "http://www.w3.org/2005/Atom",
            "arxiv": "http://arxiv.org/schemas/atom"
        }

    async def search(
        self,
        query: str,
        max_results: int = 5,
        sort_by: str = "relevance",  # relevance, lastUpdatedDate, submittedDate
        sort_order: str = "descending"
    ) -> List[Dict]:
        """
        Search ArXiv for research papers.

        Args:
            query: Search query (supports ArXiv search syntax)
            max_results: Maximum number of results
            sort_by: Sort field
            sort_order: ascending or descending

        Returns:
            List of papers with title, authors, abstract, etc.
        """
        # Build search query - search in all fields
        search_query = f"all:{query}"

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": sort_by,
            "sortOrder": sort_order,
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                return self._parse_response(response.text)

        except Exception as e:
            print(f"ArXiv search error: {e}")
            return []

    async def search_by_category(
        self,
        query: str,
        category: str,  # e.g., "cs.AI", "cs.LG", "stat.ML"
        max_results: int = 5
    ) -> List[Dict]:
        """
        Search ArXiv within a specific category.

        Common categories:
        - cs.AI: Artificial Intelligence
        - cs.LG: Machine Learning
        - cs.CL: Computation and Language (NLP)
        - cs.CV: Computer Vision
        - stat.ML: Machine Learning (Statistics)
        """
        search_query = f"all:{query} AND cat:{category}"

        params = {
            "search_query": search_query,
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                return self._parse_response(response.text)

        except Exception as e:
            print(f"ArXiv category search error: {e}")
            return []

    async def get_paper_by_id(self, arxiv_id: str) -> Optional[Dict]:
        """
        Get a specific paper by its ArXiv ID.

        Args:
            arxiv_id: ArXiv paper ID (e.g., "2301.00001")

        Returns:
            Paper details or None
        """
        params = {
            "id_list": arxiv_id,
            "max_results": 1,
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                papers = self._parse_response(response.text)
                return papers[0] if papers else None

        except Exception as e:
            print(f"ArXiv get paper error: {e}")
            return None

    async def get_recent_papers(
        self,
        category: str = "cs.AI",
        max_results: int = 10
    ) -> List[Dict]:
        """
        Get recent papers from a category.

        Args:
            category: ArXiv category
            max_results: Maximum papers to return

        Returns:
            List of recent papers
        """
        params = {
            "search_query": f"cat:{category}",
            "start": 0,
            "max_results": max_results,
            "sortBy": "submittedDate",
            "sortOrder": "descending",
        }

        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()

                return self._parse_response(response.text)

        except Exception as e:
            print(f"ArXiv recent papers error: {e}")
            return []

    def _parse_response(self, xml_text: str) -> List[Dict]:
        """Parse ArXiv API XML response."""
        papers = []

        try:
            root = ET.fromstring(xml_text)

            for entry in root.findall("atom:entry", self.namespaces):
                # Extract basic info
                title = entry.find("atom:title", self.namespaces)
                summary = entry.find("atom:summary", self.namespaces)
                published = entry.find("atom:published", self.namespaces)
                updated = entry.find("atom:updated", self.namespaces)

                # Extract authors
                authors = []
                for author in entry.findall("atom:author", self.namespaces):
                    name = author.find("atom:name", self.namespaces)
                    if name is not None:
                        authors.append(name.text)

                # Extract links
                pdf_link = None
                abs_link = None
                for link in entry.findall("atom:link", self.namespaces):
                    if link.get("title") == "pdf":
                        pdf_link = link.get("href")
                    elif link.get("type") == "text/html":
                        abs_link = link.get("href")

                # Extract ArXiv ID
                id_elem = entry.find("atom:id", self.namespaces)
                arxiv_id = ""
                if id_elem is not None:
                    arxiv_id = id_elem.text.split("/abs/")[-1]

                # Extract categories
                categories = []
                for cat in entry.findall("arxiv:primary_category", self.namespaces):
                    categories.append(cat.get("term"))
                for cat in entry.findall("atom:category", self.namespaces):
                    term = cat.get("term")
                    if term and term not in categories:
                        categories.append(term)

                paper = {
                    "arxiv_id": arxiv_id,
                    "title": self._clean_text(title.text) if title is not None else "",
                    "abstract": self._clean_text(summary.text) if summary is not None else "",
                    "authors": authors,
                    "published": published.text if published is not None else "",
                    "updated": updated.text if updated is not None else "",
                    "pdf_url": pdf_link,
                    "url": abs_link or f"https://arxiv.org/abs/{arxiv_id}",
                    "categories": categories,
                    "source": "arxiv",
                    "score": 0.85  # Base score for ArXiv results
                }

                papers.append(paper)

        except ET.ParseError as e:
            print(f"ArXiv XML parse error: {e}")

        return papers

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        if not text:
            return ""
        # Remove extra whitespace and newlines
        return " ".join(text.split())

    def format_for_rag(self, papers: List[Dict]) -> List[Dict]:
        """
        Format ArXiv papers for RAG integration.

        Returns format compatible with research agent.
        """
        formatted = []
        for paper in papers:
            # Create content combining title and abstract
            content = f"{paper['title']}\n\nAbstract: {paper['abstract']}"
            if paper["authors"]:
                content += f"\n\nAuthors: {', '.join(paper['authors'][:5])}"

            formatted.append({
                "id": f"arxiv:{paper['arxiv_id']}",
                "title": paper["title"],
                "content": content[:2000],  # Limit content length
                "source_url": paper["url"],
                "source": "arxiv",
                "score": paper.get("score", 0.85),
                "metadata": {
                    "authors": paper["authors"],
                    "categories": paper["categories"],
                    "published": paper["published"],
                }
            })

        return formatted


# Singleton instance
arxiv_service = ArxivService()
