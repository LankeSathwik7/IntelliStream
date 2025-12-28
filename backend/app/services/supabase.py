"""Supabase client service."""

from functools import lru_cache
from typing import Any, Dict, List, Optional

from supabase import Client, create_client

from app.config import settings


@lru_cache
def get_supabase_client() -> Client:
    """Get cached Supabase client."""
    return create_client(
        settings.supabase_url,
        settings.supabase_service_role_key,
    )


class SupabaseService:
    """Supabase database operations."""

    def __init__(self):
        self._client: Optional[Client] = None

    @property
    def client(self) -> Client:
        """Lazy-load Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # ==================
    # DOCUMENT OPERATIONS
    # ==================

    async def insert_document(
        self,
        title: str,
        content: str,
        embedding: List[float],
        source_url: Optional[str] = None,
        source_type: str = "custom",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Insert a document with its embedding."""
        data = {
            "title": title,
            "content": content,
            "embedding": embedding,
            "source_url": source_url,
            "source_type": source_type,
            "metadata": metadata or {},
        }

        result = self.client.table("documents").insert(data).execute()
        return result.data[0] if result.data else {}

    async def search_documents(
        self,
        query_embedding: List[float],
        match_count: int = 10,
        source_type: Optional[str] = None,
    ) -> List[Dict]:
        """Vector similarity search using RPC function."""
        result = self.client.rpc(
            "match_documents",
            {
                "query_embedding": query_embedding,
                "match_count": match_count,
                "filter_source_type": source_type,
            },
        ).execute()

        return result.data or []

    async def hybrid_search(
        self,
        query_text: str,
        query_embedding: List[float],
        match_count: int = 10,
    ) -> List[Dict]:
        """Hybrid search combining vector and keyword."""
        result = self.client.rpc(
            "hybrid_search",
            {
                "query_text": query_text,
                "query_embedding": query_embedding,
                "match_count": match_count,
            },
        ).execute()

        return result.data or []

    async def get_documents(
        self,
        limit: int = 10,
        offset: int = 0,
        source_type: Optional[str] = None,
    ) -> List[Dict]:
        """Get documents with pagination."""
        query = self.client.table("documents").select("*")

        if source_type:
            query = query.eq("source_type", source_type)

        result = query.range(offset, offset + limit - 1).execute()
        return result.data or []

    async def delete_document(self, document_id: str) -> bool:
        """Delete a document by ID."""
        result = (
            self.client.table("documents").delete().eq("id", document_id).execute()
        )
        return len(result.data) > 0

    # ==================
    # THREAD OPERATIONS
    # ==================

    async def create_thread(
        self, user_id: Optional[str] = None, title: Optional[str] = None
    ) -> Dict:
        """Create a new conversation thread."""
        data = {"title": title}
        if user_id:
            data["user_id"] = user_id
        result = self.client.table("threads").insert(data).execute()
        return result.data[0] if result.data else {}

    async def get_thread_messages(
        self,
        thread_id: str,
        limit: int = 50,
    ) -> List[Dict]:
        """Get messages in a thread."""
        result = (
            self.client.table("messages")
            .select("*")
            .eq("thread_id", thread_id)
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None,
        agent_trace: Optional[List[Dict]] = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
    ) -> Dict:
        """Add a message to a thread."""
        data = {
            "thread_id": thread_id,
            "role": role,
            "content": content,
            "sources": sources or [],
            "agent_trace": agent_trace or [],
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
        }
        result = self.client.table("messages").insert(data).execute()
        return result.data[0] if result.data else {}

    # ==================
    # AGENT LOG OPERATIONS
    # ==================

    async def log_agent_execution(
        self,
        thread_id: str,
        message_id: str,
        agent_name: str,
        action: str,
        input_state: Optional[Dict] = None,
        output_state: Optional[Dict] = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
        error: Optional[str] = None,
    ) -> Dict:
        """Log agent execution for observability."""
        data = {
            "thread_id": thread_id,
            "message_id": message_id,
            "agent_name": agent_name,
            "action": action,
            "input_state": input_state,
            "output_state": output_state,
            "tokens_used": tokens_used,
            "latency_ms": latency_ms,
            "error": error,
        }
        result = self.client.table("agent_logs").insert(data).execute()
        return result.data[0] if result.data else {}

    # ==================
    # USER SETTINGS OPERATIONS
    # ==================

    async def get_user_settings(self, user_id: str) -> Optional[Dict]:
        """Get settings for a user."""
        try:
            result = (
                self.client.table("user_settings")
                .select("*")
                .eq("user_id", user_id)
                .single()
                .execute()
            )
            return result.data
        except Exception:
            return None

    async def upsert_user_settings(self, user_id: str, settings: Dict) -> Dict:
        """Create or update user settings."""
        data = {
            "user_id": user_id,
            "theme": settings.get("theme", "light"),
            "sound_enabled": settings.get("soundEnabled", True),
            "notifications_enabled": settings.get("notificationsEnabled", True),
            "streaming_speed": settings.get("streamingSpeed", "medium"),
        }
        result = (
            self.client.table("user_settings")
            .upsert(data, on_conflict="user_id")
            .execute()
        )
        return result.data[0] if result.data else {}


# Singleton instance
supabase_service = SupabaseService()
