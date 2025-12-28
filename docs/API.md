# IntelliStream API Documentation

## Overview

IntelliStream is a Real-Time Agentic RAG Intelligence Platform with a 6-agent LangGraph workflow. This document provides comprehensive API documentation for enterprise integration.

**Base URL:** `https://your-domain.com/api`
**Version:** 1.0.0
**Authentication:** Bearer Token (Supabase JWT)

---

## Authentication

### Overview

IntelliStream uses Supabase Auth for authentication. All authenticated endpoints require a Bearer token in the Authorization header.

```http
Authorization: Bearer <your-jwt-token>
```

### Roles

| Role | Description | Rate Limits |
|------|-------------|-------------|
| `anonymous` | Unauthenticated users | 10/min, 50/hour, 200/day |
| `user` | Basic authenticated users | 20/min, 200/hour, 2000/day |
| `premium` | Premium users | 60/min, 1000/hour, 10000/day |
| `admin` | Administrators | 120/min, 2000/hour, 20000/day |

### Getting a Token

```bash
# Sign up
curl -X POST "https://your-supabase.supabase.co/auth/v1/signup" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Sign in
curl -X POST "https://your-supabase.supabase.co/auth/v1/token?grant_type=password" \
  -H "apikey: YOUR_ANON_KEY" \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'
```

---

## Endpoints

### Health Check

#### GET /health

Check API health status.

**Response:**
```json
{
  "status": "healthy",
  "service": "intellistream-api",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### GET /health/live

Kubernetes liveness probe.

**Response:**
```json
{
  "status": "alive"
}
```

#### GET /health/ready

Kubernetes readiness probe with dependency checks.

**Response:**
```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "cache": "ok",
    "llm": "ok"
  }
}
```

---

### Chat

#### POST /api/chat

Send a message and receive a response.

**Request:**
```json
{
  "message": "What is machine learning?",
  "thread_id": "optional-uuid",
  "sources": ["news", "research", "wikipedia"]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `message` | string | Yes | User message (max 10,000 chars) |
| `thread_id` | string | No | Conversation thread ID (UUID) |
| `sources` | array | No | Data sources to search |

**Response:**
```json
{
  "response": "Machine learning is a subset of artificial intelligence...",
  "thread_id": "550e8400-e29b-41d4-a716-446655440000",
  "sources": [
    {
      "id": "[1]",
      "title": "Wikipedia: Machine Learning",
      "url": "https://en.wikipedia.org/wiki/Machine_learning",
      "snippet": "Machine learning (ML) is a field of study...",
      "score": 0.92
    }
  ],
  "agent_trace": [
    {"agent": "router", "action": "research", "latency_ms": 45},
    {"agent": "research", "action": "wiki+rag", "latency_ms": 320},
    {"agent": "analysis", "action": "extracted_entities", "latency_ms": 150},
    {"agent": "synthesizer", "action": "generated", "latency_ms": 280},
    {"agent": "reflection", "action": "enhanced", "latency_ms": 200},
    {"agent": "response", "action": "formatted", "latency_ms": 50}
  ],
  "latency_ms": 1045
}
```

**Error Responses:**

| Status | Description |
|--------|-------------|
| 400 | Invalid input (empty message, injection detected) |
| 401 | Authentication required |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

#### POST /api/chat/stream

Stream response using Server-Sent Events (SSE).

**Request:** Same as `/api/chat`

**Response:** SSE stream

```
data: {"type": "agent_status", "data": {"agent": "router", "status": "started"}}

data: {"type": "agent_status", "data": {"agent": "router", "status": "completed"}}

data: {"type": "agent_status", "data": {"agent": "research", "status": "started"}}

data: {"type": "response", "data": {"content": "Machine learning is...", "sources": [...]}}

data: {"type": "done", "data": {"thread_id": "..."}}
```

---

### Documents

#### GET /api/documents

List all documents.

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `limit` | int | 10 | Results per page (max 100) |
| `offset` | int | 0 | Pagination offset |
| `source_type` | string | - | Filter by type |

**Response:**
```json
{
  "documents": [
    {
      "id": "doc-uuid",
      "title": "Document Title",
      "source_type": "research",
      "created_at": "2024-01-15T10:00:00Z",
      "chunk_count": 5
    }
  ],
  "total": 42,
  "limit": 10,
  "offset": 0
}
```

#### POST /api/documents

Create a new document.

**Request:**
```json
{
  "title": "Research Paper Title",
  "content": "Full document content...",
  "source_type": "research",
  "source_url": "https://example.com/paper.pdf",
  "metadata": {
    "author": "John Doe",
    "year": 2024
  }
}
```

**Response:**
```json
{
  "id": "new-doc-uuid",
  "title": "Research Paper Title",
  "source_type": "research",
  "created_at": "2024-01-15T10:30:00Z",
  "chunk_count": 12
}
```

#### POST /api/documents/search

Search documents using semantic search.

**Request:**
```json
{
  "query": "machine learning algorithms",
  "top_k": 5,
  "source_types": ["research", "documentation"]
}
```

**Response:**
```json
{
  "results": [
    {
      "id": "doc-uuid",
      "title": "ML Algorithms Overview",
      "content": "Matching content snippet...",
      "score": 0.89,
      "source_url": "https://example.com"
    }
  ],
  "total": 5
}
```

#### POST /api/documents/upload

Upload a file (PDF, DOCX, TXT).

**Request:**
```
Content-Type: multipart/form-data

file: <binary>
source_type: research
```

**Constraints:**
- Max file size: 10MB
- Allowed types: .pdf, .docx, .txt, .md

**Response:**
```json
{
  "id": "uploaded-doc-uuid",
  "title": "Uploaded Document",
  "source_type": "research",
  "file_type": "pdf",
  "size_bytes": 1048576,
  "chunk_count": 25
}
```

#### DELETE /api/documents/{id}

Delete a document.

**Response:**
```json
{
  "success": true,
  "message": "Document deleted"
}
```

---

## Real-Time Data

IntelliStream automatically detects and fetches real-time data for specific query types:

### Weather Queries

Detected keywords: weather, temperature, forecast, rain, sunny, etc.

**Example:**
```json
{
  "message": "What's the weather in Tokyo?"
}
```

**Response includes:**
```json
{
  "sources": [
    {
      "id": "weather_Tokyo",
      "title": "Weather: Tokyo",
      "content": "Current weather in Tokyo, JP:\nTemperature: 15°C (feels like 14°C)\nConditions: cloudy\nHumidity: 65%\nWind: 5.5 m/s",
      "score": 0.95
    }
  ]
}
```

### Stock Queries

Detected: stock, $AAPL, $TSLA, ticker, market, etc.

**Example:**
```json
{
  "message": "What's the current price of AAPL?"
}
```

### News Queries

Detected: latest news, headlines, breaking, current events, etc.

**Example:**
```json
{
  "message": "What are the latest AI headlines?"
}
```

### Research Queries

Detected: research paper, arxiv, scientific study, etc.

**Example:**
```json
{
  "message": "Latest transformer architecture papers"
}
```

---

## Rate Limiting

Rate limits are applied per user (authenticated) or per IP (anonymous).

**Headers in Response:**
```http
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 29
X-RateLimit-Reset: 1705315800
```

**Rate Limit Exceeded Response:**
```json
{
  "error": "Rate limit exceeded",
  "retry_after": 45,
  "limit": 30,
  "remaining": 0
}
```

---

## Error Handling

### Error Response Format

```json
{
  "detail": "Error description",
  "error_code": "VALIDATION_ERROR",
  "request_id": "abc123",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Invalid request data |
| `AUTHENTICATION_ERROR` | 401 | Missing or invalid token |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `NOT_FOUND` | 404 | Resource not found |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `CIRCUIT_BREAKER_OPEN` | 503 | Service temporarily unavailable |
| `INTERNAL_ERROR` | 500 | Unexpected server error |

---

## WebSocket Support (Future)

*Coming soon*

---

## SDK Examples

### Python

```python
import httpx

async def chat(message: str, token: str = None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.intellistream.com/api/chat",
            json={"message": message},
            headers=headers
        )
        return response.json()
```

### JavaScript/TypeScript

```typescript
async function chat(message: string, token?: string): Promise<ChatResponse> {
  const response = await fetch('https://api.intellistream.com/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    },
    body: JSON.stringify({ message })
  });

  return response.json();
}
```

### Streaming Example (JavaScript)

```typescript
async function streamChat(message: string) {
  const response = await fetch('https://api.intellistream.com/api/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message })
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();

  while (true) {
    const { done, value } = await reader!.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split('\n');

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const event = JSON.parse(line.slice(6));
        console.log(event.type, event.data);
      }
    }
  }
}
```

---

## OpenAPI Specification

Full OpenAPI 3.0 specification available at:
- Development: `http://localhost:8000/docs`
- Production: Disabled for security

---

## Changelog

### v1.0.0 (2024-01-15)

- Initial release
- 6-agent workflow (Router, Research, Analysis, Synthesis, Reflection, Response)
- Real-time data integration (Weather, News, Stocks)
- Wikipedia and ArXiv search
- Multi-modal support (Images, Audio, PDF, DOCX)
- Role-based access control
- Rate limiting with Redis
- Circuit breaker pattern

---

## Support

- GitHub Issues: https://github.com/intellistream/intellistream/issues
- Documentation: https://docs.intellistream.com
