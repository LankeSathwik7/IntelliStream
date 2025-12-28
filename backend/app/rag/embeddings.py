"""Embedding generation using Voyage AI API."""

import asyncio
from typing import List

import httpx

from app.config import settings


class EmbeddingServiceError(Exception):
    """Custom exception for embedding service errors."""
    pass


class EmbeddingService:
    """Generate embeddings using Voyage AI REST API."""

    def __init__(self):
        self.api_url = "https://api.voyageai.com/v1/embeddings"
        self.model = "voyage-2"
        self.max_retries = 15  # More retries for rate limiting
        self.base_delay = 10.0  # Start with 10 second delay
        self.max_delay = 120.0  # Cap at 2 minutes
        print("[EMBED] Using VoyageAI embeddings (voyage-2) - may be slow due to rate limits")

    def _check_api_key(self):
        """Check if API key is configured."""
        key = settings.voyage_api_key
        if not key or key.startswith("your_") or len(key) < 10:
            raise EmbeddingServiceError("Voyage AI API key not configured.")

    def _get_headers(self) -> dict:
        """Get API headers."""
        return {
            "Authorization": f"Bearer {settings.voyage_api_key}",
            "Content-Type": "application/json",
        }

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a search query."""
        self._check_api_key()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                self.api_url,
                headers=self._get_headers(),
                json={
                    "input": [text],
                    "model": self.model,
                    "input_type": "query",
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]

    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for documents (batch) with retry logic."""
        self._check_api_key()
        all_embeddings = []
        batch_size = 2  # Small batches to avoid rate limits
        total_batches = (len(texts) + batch_size - 1) // batch_size

        print(f"[EMBED] Processing {len(texts)} texts in {total_batches} batches (this may take a while due to rate limits)")

        async with httpx.AsyncClient() as client:
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                batch_num = i // batch_size + 1

                for attempt in range(self.max_retries):
                    try:
                        response = await client.post(
                            self.api_url,
                            headers=self._get_headers(),
                            json={
                                "input": batch,
                                "model": self.model,
                                "input_type": "document",
                            },
                            timeout=120.0,
                        )

                        if response.status_code == 429:
                            delay = min(self.base_delay * (1.5 ** attempt), self.max_delay)
                            print(f"[EMBED] Rate limited, waiting {delay:.0f}s (attempt {attempt + 1}/{self.max_retries})")
                            await asyncio.sleep(delay)
                            continue

                        response.raise_for_status()
                        data = response.json()
                        all_embeddings.extend([item["embedding"] for item in data["data"]])
                        print(f"[EMBED] Batch {batch_num}/{total_batches} done ({len(all_embeddings)}/{len(texts)} texts)")
                        break

                    except httpx.HTTPStatusError as e:
                        if e.response.status_code == 429 and attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (1.5 ** attempt), self.max_delay)
                            print(f"[EMBED] Rate limited, waiting {delay:.0f}s")
                            await asyncio.sleep(delay)
                            continue
                        raise
                    except Exception as e:
                        if attempt < self.max_retries - 1:
                            delay = min(self.base_delay * (1.5 ** attempt), self.max_delay)
                            print(f"[EMBED] Error: {e}, retrying in {delay:.0f}s")
                            await asyncio.sleep(delay)
                            continue
                        raise
                else:
                    raise EmbeddingServiceError(f"Failed after {self.max_retries} retries")

                # Delay between batches
                if i + batch_size < len(texts):
                    await asyncio.sleep(5.0)

        print(f"[EMBED] All {len(texts)} texts embedded successfully!")
        return all_embeddings

    async def embed_single(self, text: str, input_type: str = "document") -> List[float]:
        """Generate embedding for a single text with retry logic."""
        self._check_api_key()

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.api_url,
                        headers=self._get_headers(),
                        json={
                            "input": [text],
                            "model": self.model,
                            "input_type": input_type,
                        },
                        timeout=60.0,
                    )

                    if response.status_code == 429:
                        delay = min(self.base_delay * (1.5 ** attempt), self.max_delay)
                        print(f"[EMBED] Rate limited, waiting {delay:.0f}s (attempt {attempt + 1}/{self.max_retries})")
                        await asyncio.sleep(delay)
                        continue

                    response.raise_for_status()
                    data = response.json()
                    return data["data"][0]["embedding"]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429 and attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (1.5 ** attempt), self.max_delay)
                    print(f"[EMBED] Rate limited, waiting {delay:.0f}s")
                    await asyncio.sleep(delay)
                    continue
                raise
            except Exception as e:
                if attempt < self.max_retries - 1:
                    delay = min(self.base_delay * (1.5 ** attempt), self.max_delay)
                    print(f"[EMBED] Error: {e}, retrying in {delay:.0f}s")
                    await asyncio.sleep(delay)
                    continue
                raise

        raise EmbeddingServiceError(f"Failed after {self.max_retries} retries")


# Singleton instance
embedding_service = EmbeddingService()
