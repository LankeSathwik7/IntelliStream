"""Groq LLM service for agent inference."""

import json
from functools import lru_cache
from typing import Any, AsyncGenerator, Dict, List, Optional

from groq import AsyncGroq

from app.config import settings


@lru_cache
def get_groq_client() -> AsyncGroq:
    """Get cached Groq client."""
    return AsyncGroq(api_key=settings.groq_api_key)


class LLMService:
    """Groq LLM operations."""

    def __init__(self):
        self._client: Optional[AsyncGroq] = None
        self.default_model = "llama-3.3-70b-versatile"  # Best for complex reasoning
        self.fast_model = "llama-3.1-8b-instant"  # For routing/simple tasks

    @property
    def client(self) -> AsyncGroq:
        """Lazy-load Groq client."""
        if self._client is None:
            self._client = get_groq_client()
        return self._client

    async def generate(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Generate a response (non-streaming)."""
        model = model or self.default_model

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        response = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response.choices[0].message.content or ""

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Generate a streaming response."""
        model = model or self.default_model

        full_messages = []
        if system_prompt:
            full_messages.append({"role": "system", "content": system_prompt})
        full_messages.extend(messages)

        stream = await self.client.chat.completions.create(
            model=model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )

        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_json(
        self,
        messages: List[Dict[str, str]],
        schema_description: str,
        model: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON output."""
        model = model or self.default_model

        system_prompt = f"""You are a helpful assistant that always responds with valid JSON.
Your response must match this schema:
{schema_description}

Respond ONLY with valid JSON, no markdown, no explanation."""

        response = await self.generate(
            messages=messages,
            model=model,
            system_prompt=system_prompt,
            temperature=0.3,  # Lower temperature for structured output
        )

        # Clean and parse JSON
        response = response.strip()
        if response.startswith("```json"):
            response = response[7:]
        if response.startswith("```"):
            response = response[3:]
        if response.endswith("```"):
            response = response[:-3]

        try:
            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Return a default structure if parsing fails
            return {"error": "Failed to parse JSON response"}

    async def route_query(self, query: str) -> str:
        """Classify a query to determine routing (fast model)."""
        system_prompt = """Classify the user query into one of these categories:
- RESEARCH: Requires searching documents/knowledge base
- DIRECT: Can be answered directly without search
- CLARIFY: Query is unclear, needs clarification

Respond with ONLY the category name."""

        response = await self.generate(
            messages=[{"role": "user", "content": query}],
            model=self.fast_model,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=20,
        )

        return response.strip().upper()


# Singleton instance
llm_service = LLMService()
