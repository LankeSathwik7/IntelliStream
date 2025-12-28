"""Memory service for conversation persistence using Supabase."""

from typing import List, Dict, Optional
from datetime import datetime
from app.services.supabase import supabase_service


class MemoryService:
    """Manage conversation memory across sessions."""

    def __init__(self, max_messages: int = 20):
        self.max_messages = max_messages

    async def get_conversation_history(
        self,
        thread_id: str,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Get conversation history for a thread.

        Args:
            thread_id: Thread ID
            limit: Max messages to return (default: max_messages)

        Returns:
            List of messages in chronological order
        """
        limit = limit or self.max_messages

        try:
            messages = await supabase_service.get_thread_messages(
                thread_id=thread_id,
                limit=limit
            )

            return [
                {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                    "timestamp": msg.get("created_at"),
                }
                for msg in messages
            ]

        except Exception as e:
            print(f"Error getting conversation history: {e}")
            return []

    async def add_message(
        self,
        thread_id: str,
        role: str,
        content: str,
        sources: Optional[List[Dict]] = None,
        agent_trace: Optional[List[Dict]] = None,
        latency_ms: int = 0
    ) -> Optional[Dict]:
        """
        Add a message to conversation history.

        Args:
            thread_id: Thread ID
            role: Message role (user/assistant/system)
            content: Message content
            sources: Source citations
            agent_trace: Agent execution trace
            latency_ms: Response latency

        Returns:
            Created message or None
        """
        try:
            message = await supabase_service.add_message(
                thread_id=thread_id,
                role=role,
                content=content,
                sources=sources,
                agent_trace=agent_trace,
                latency_ms=latency_ms
            )
            return message

        except Exception as e:
            print(f"Error adding message: {e}")
            return None

    async def create_thread(
        self,
        user_id: Optional[str] = None,
        title: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new conversation thread.

        Returns:
            Thread ID or None
        """
        try:
            thread = await supabase_service.create_thread(
                user_id=user_id or "anonymous",
                title=title
            )
            return thread.get("id") if thread else None

        except Exception as e:
            print(f"Error creating thread: {e}")
            return None

    async def get_or_create_thread(
        self,
        thread_id: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> str:
        """
        Get existing thread or create new one.

        Returns:
            Thread ID
        """
        if thread_id:
            # Verify thread exists
            try:
                messages = await supabase_service.get_thread_messages(thread_id, limit=1)
                return thread_id
            except:
                pass

        # Create new thread
        new_id = await self.create_thread(user_id=user_id)
        return new_id or thread_id or "default"

    def format_history_for_llm(
        self,
        messages: List[Dict],
        max_tokens: int = 4000
    ) -> List[Dict]:
        """
        Format conversation history for LLM context.

        Args:
            messages: List of messages
            max_tokens: Approximate token limit

        Returns:
            Formatted messages for LLM
        """
        formatted = []
        total_chars = 0
        char_limit = max_tokens * 4  # Rough char-to-token ratio

        # Process from most recent to oldest
        for msg in reversed(messages):
            content = msg.get("content", "")
            role = msg.get("role", "user")

            if total_chars + len(content) > char_limit:
                break

            formatted.insert(0, {
                "role": role,
                "content": content
            })
            total_chars += len(content)

        return formatted

    async def get_thread_summary(self, thread_id: str) -> Optional[Dict]:
        """
        Get a summary of a conversation thread.

        Returns:
            Thread summary with message count, topics, etc.
        """
        try:
            messages = await supabase_service.get_thread_messages(
                thread_id=thread_id,
                limit=100
            )

            if not messages:
                return None

            user_messages = [m for m in messages if m.get("role") == "user"]
            assistant_messages = [m for m in messages if m.get("role") == "assistant"]

            # Extract first message as title
            first_user = user_messages[0] if user_messages else None
            title = first_user.get("content", "")[:50] if first_user else "Untitled"

            return {
                "thread_id": thread_id,
                "title": title,
                "message_count": len(messages),
                "user_messages": len(user_messages),
                "assistant_messages": len(assistant_messages),
                "created_at": messages[0].get("created_at") if messages else None,
                "last_activity": messages[-1].get("created_at") if messages else None,
            }

        except Exception as e:
            print(f"Error getting thread summary: {e}")
            return None


# Singleton instance
memory_service = MemoryService()
