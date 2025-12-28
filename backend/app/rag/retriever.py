"""Hybrid retrieval system combining vector and keyword search."""

from typing import Dict, List, Optional, Tuple

from app.rag.embeddings import embedding_service
from app.services.cache import cache_service
from app.services.supabase import supabase_service


class HybridRetriever:
    """
    Hybrid retrieval combining:
    1. Vector similarity search (semantic)
    2. Keyword search (BM25-style)
    3. Optional reranking
    """

    def __init__(
        self,
        vector_weight: float = 0.6,
        keyword_weight: float = 0.4,
    ):
        self.vector_weight = vector_weight
        self.keyword_weight = keyword_weight

    async def retrieve(
        self,
        query: str,
        top_k: int = 10,
        source_type: Optional[str] = None,
        use_cache: bool = True,
    ) -> List[Dict]:
        """
        Retrieve relevant documents using hybrid search.

        Args:
            query: Search query
            top_k: Number of results to return
            source_type: Filter by source type
            use_cache: Whether to use cached results

        Returns:
            List of relevant documents with scores
        """
        # Check cache first
        if use_cache:
            cached = await cache_service.get_search_result(query)
            if cached:
                return cached.get("documents", [])[:top_k]

        # Generate query embedding
        query_embedding = await self._get_query_embedding(query)

        # Perform hybrid search using Supabase RPC
        try:
            results = await supabase_service.hybrid_search(
                query_text=query,
                query_embedding=query_embedding,
                match_count=top_k * 2,  # Get more for reranking
            )
        except Exception:
            # Fallback to vector-only search if hybrid fails
            results = await supabase_service.search_documents(
                query_embedding=query_embedding,
                match_count=top_k * 2,
                source_type=source_type,
            )

        # Format results
        documents = [
            {
                "id": doc.get("id", ""),
                "title": doc.get("title", ""),
                "content": doc.get("content", ""),
                "source_url": doc.get("source_url"),
                "score": doc.get("combined_score", doc.get("similarity", 0)),
            }
            for doc in results
        ]

        # Sort by score and limit
        documents.sort(key=lambda x: x["score"], reverse=True)
        documents = documents[:top_k]

        # Cache results
        if use_cache and documents:
            await cache_service.set_search_result(
                query,
                {"documents": documents},
                ttl=1800,  # 30 minutes
            )

        return documents

    async def retrieve_with_context(
        self,
        query: str,
        top_k: int = 5,
        context_window: int = 500,
    ) -> Tuple[List[Dict], str]:
        """
        Retrieve documents and format as context string.

        Returns:
            Tuple of (documents, formatted_context)
        """
        documents = await self.retrieve(query, top_k=top_k)

        if not documents:
            return [], "No relevant documents found."

        # Format context for LLM
        context_parts = []
        for i, doc in enumerate(documents, 1):
            content = doc["content"]
            if len(content) > context_window:
                content = content[:context_window] + "..."

            context_parts.append(f"[{i}] {doc['title']}\n{content}")

        context = "\n\n---\n\n".join(context_parts)

        return documents, context

    async def _get_query_embedding(self, query: str) -> List[float]:
        """Get embedding for query with caching."""
        # Check cache
        cached = await cache_service.get_embedding(query)
        if cached:
            return cached

        # Generate embedding
        embedding = await embedding_service.embed_query(query)

        # Cache it
        await cache_service.set_embedding(query, embedding)

        return embedding

    async def add_document(
        self,
        title: str,
        content: str,
        source_url: Optional[str] = None,
        source_type: str = "custom",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Add a document to the knowledge base."""
        # Generate embedding
        embedding = await embedding_service.embed_single(content, input_type="document")

        # Insert into Supabase
        document = await supabase_service.insert_document(
            title=title,
            content=content,
            embedding=embedding,
            source_url=source_url,
            source_type=source_type,
            metadata=metadata,
        )

        return document

    async def add_documents_batch(
        self,
        documents: List[Dict],
    ) -> List[Dict]:
        """
        Add multiple documents at once with batch embedding.
        Much faster than adding one by one.

        Args:
            documents: List of dicts with keys: title, content, source_url, source_type, metadata

        Returns:
            List of created documents
        """
        if not documents:
            return []

        # Extract all content for batch embedding
        contents = [doc["content"] for doc in documents]

        # Generate all embeddings in one batch call
        embeddings = await embedding_service.embed_documents(contents)

        # Insert all documents
        created = []
        for doc, embedding in zip(documents, embeddings):
            result = await supabase_service.insert_document(
                title=doc["title"],
                content=doc["content"],
                embedding=embedding,
                source_url=doc.get("source_url"),
                source_type=doc.get("source_type", "custom"),
                metadata=doc.get("metadata"),
            )
            created.append(result)

        return created


# Singleton instance
retriever = HybridRetriever()
