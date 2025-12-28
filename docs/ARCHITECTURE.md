# IntelliStream Architecture Documentation

## System Overview

IntelliStream is a Real-Time Agentic RAG (Retrieval-Augmented Generation) Intelligence Platform designed for enterprise use. It uses a 6-agent LangGraph workflow to process queries, retrieve relevant information, and generate intelligent responses.

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    CLIENT LAYER                                           │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐                        │
│  │   Web Client     │  │   Mobile App     │  │   API Client     │                        │
│  │   (Next.js 15)   │  │   (Future)       │  │   (SDK)          │                        │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘                        │
│           └─────────────────────┼─────────────────────┘                                  │
│                                 ▼                                                        │
│  ┌──────────────────────────────────────────────────────────────────────────────────┐   │
│  │                           API GATEWAY (FastAPI)                                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │   │
│  │  │   CORS   │  │   Auth   │  │   Rate   │  │  Logging │  │   Observability  │    │   │
│  │  │Middleware│  │Middleware│  │  Limit   │  │Middleware│  │   (Tracing)      │    │   │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  └──────────────────┘    │   │
│  └──────────────────────────────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                  APPLICATION LAYER                                        │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                          6-Agent LangGraph Workflow                                 │  │
│  │                                                                                     │  │
│  │  START ──► ┌────────┐     ┌──────────┐     ┌──────────┐     ┌───────────┐          │  │
│  │            │ Router │────►│ Research │────►│ Analysis │────►│ Synthesis │          │  │
│  │            └────┬───┘     └──────────┘     └──────────┘     └─────┬─────┘          │  │
│  │                 │              │                                   │               │  │
│  │                 │              ▼                                   ▼               │  │
│  │                 │    ┌─────────────────────────────────────────────────────┐       │  │
│  │                 │    │              DATA SOURCES                            │       │  │
│  │                 │    │  ┌─────┐ ┌─────┐ ┌──────┐ ┌─────┐ ┌─────┐ ┌──────┐  │       │  │
│  │                 │    │  │ RAG │ │Wiki │ │ArXiv │ │News │ │Stock│ │Weather│ │       │  │
│  │                 │    │  └─────┘ └─────┘ └──────┘ └─────┘ └─────┘ └──────┘  │       │  │
│  │                 │    └─────────────────────────────────────────────────────┘       │  │
│  │                 │                                                                  │  │
│  │                 │         ┌────────────┐     ┌──────────┐                          │  │
│  │                 └────────►│ Reflection │────►│ Response │────► END                 │  │
│  │                           └────────────┘     └──────────┘                          │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                          │
│  ┌────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              SERVICE LAYER                                          │  │
│  │  ┌───────────┐ ┌────────────┐ ┌──────────┐ ┌────────────┐ ┌──────────────────────┐ │  │
│  │  │ LLM       │ │ Embedding  │ │ Document │ │ Multi-     │ │ External APIs        │ │  │
│  │  │ Service   │ │ Service    │ │ Processor│ │ Modal      │ │ (Web,News,Weather...)│ │  │
│  │  │ (Groq)    │ │ (Voyage)   │ │          │ │ (Vision,   │ │                      │ │  │
│  │  │           │ │            │ │          │ │  Audio)    │ │                      │ │  │
│  │  └───────────┘ └────────────┘ └──────────┘ └────────────┘ └──────────────────────┘ │  │
│  └────────────────────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                                    DATA LAYER                                             │
│  ┌───────────────────────┐  ┌───────────────────────┐  ┌───────────────────────────────┐ │
│  │   Supabase           │  │   Upstash Redis       │  │   External Services           │ │
│  │   ├── PostgreSQL     │  │   ├── Caching         │  │   ├── Groq (LLM)              │ │
│  │   ├── pgvector       │  │   ├── Rate Limiting   │  │   ├── Voyage AI (Embeddings)  │ │
│  │   ├── Auth           │  │   └── Session Store   │  │   ├── Tavily (Web Search)     │ │
│  │   └── Row Level Sec. │  │                        │  │   ├── NewsAPI                 │ │
│  └───────────────────────┘  └───────────────────────┘  │   ├── OpenWeatherMap          │ │
│                                                        │   ├── Alpha Vantage (Stocks)  │ │
│                                                        │   └── Axiom (Monitoring)      │ │
│                                                        └───────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

## Agent Workflow

### 1. Router Agent

**Purpose:** Classify incoming queries and route to appropriate path.

**Routes:**
- `research` → Full agent pipeline for complex queries
- `direct` → Simple response for greetings/basic questions
- `clarify` → Request more information from user

**Decision Logic:**
- Detects real-time queries (weather, stocks, news)
- Identifies research/academic queries
- Classifies factual vs. conversational queries

### 2. Research Agent

**Purpose:** Retrieve relevant context from multiple sources.

**Data Sources:**
| Source | Trigger Keywords | Priority |
|--------|-----------------|----------|
| RAG (Local) | All queries | High |
| Wikipedia | "what is", "define", "who is" | Medium |
| ArXiv | "research", "paper", "study" | Medium |
| Web Search | Low RAG results | Low |
| Weather API | "weather", "temperature" | High |
| News API | "news", "headlines" | High |
| Stock API | "$AAPL", "stock price" | High |

### 3. Analysis Agent

**Purpose:** Extract insights from retrieved documents.

**Extracts:**
- Named entities (people, organizations, concepts)
- Key points and themes
- Sentiment analysis
- Relevance scoring

### 4. Synthesizer Agent

**Purpose:** Generate coherent response from analysis.

**Features:**
- Combines multiple sources
- Maintains context coherence
- Adds source citations
- Formats for readability

### 5. Reflection Agent

**Purpose:** Self-improve response quality.

**Checks:**
- Completeness (all query aspects addressed)
- Accuracy (consistent with sources)
- Clarity (well-structured)
- Citation correctness

### 6. Response Agent

**Purpose:** Final formatting and delivery.

**Tasks:**
- Format markdown
- Attach sources
- Calculate latency
- Prepare for streaming

---

## Design Decisions (ADRs)

### ADR-001: LangGraph for Workflow Orchestration

**Status:** Accepted

**Context:** Need orchestration framework for multi-agent system.

**Decision:** Use LangGraph over alternatives (CrewAI, AutoGen).

**Rationale:**
- Native Python async support
- Explicit state management
- Flexible conditional routing
- Production-ready checkpointing
- Active development by LangChain

### ADR-002: Supabase for Database

**Status:** Accepted

**Context:** Need PostgreSQL with vector search.

**Decision:** Use Supabase with pgvector extension.

**Rationale:**
- Managed PostgreSQL
- Built-in pgvector for embeddings
- Row Level Security for multi-tenancy
- Generous free tier (500MB)
- Built-in Auth

### ADR-003: Groq for LLM

**Status:** Accepted

**Context:** Need fast, cost-effective LLM.

**Decision:** Use Groq with llama-3.3-70b.

**Rationale:**
- Extremely fast inference (~150 tokens/sec)
- Free tier (30 req/min)
- Supports vision (llama-3.2-90b-vision)
- Supports audio (whisper-large-v3)
- No cold starts

### ADR-004: Voyage AI for Embeddings

**Status:** Accepted

**Context:** Need high-quality embeddings.

**Decision:** Use Voyage AI voyage-3 model.

**Rationale:**
- State-of-the-art embedding quality
- 1024-dimension vectors
- 200M tokens free tier
- Optimized for RAG

### ADR-005: SSE for Streaming

**Status:** Accepted

**Context:** Need real-time response streaming.

**Decision:** Use Server-Sent Events (SSE) over WebSocket.

**Rationale:**
- Simpler implementation
- Native browser support
- Works with HTTP/1.1 and HTTP/2
- Better for unidirectional data flow
- Automatic reconnection

### ADR-006: Self-Reflection Agent

**Status:** Accepted

**Context:** Need to improve response quality.

**Decision:** Add dedicated Reflection agent to pipeline.

**Rationale:**
- Catches incomplete responses
- Improves citation accuracy
- Adds missing context
- ~10-15% quality improvement
- Minimal latency impact (~200ms)

---

## Security Architecture

### Authentication Flow

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  Client  │──────►│   Supabase   │──────►│  IntelliStream│
│          │◄──────│     Auth     │◄──────│     API      │
└──────────┘  JWT  └──────────────┘       └──────────────┘
```

### Authorization (RBAC)

```
Role Hierarchy:
  superadmin
       │
     admin
       │
    premium
       │
      user
       │
   anonymous
```

### Input Validation

All inputs validated for:
- SQL injection patterns
- Command injection patterns
- Path traversal attacks
- HTML/XSS content
- Size limits

---

## Resilience Patterns

### Circuit Breaker

```
CLOSED ──(failures > threshold)──► OPEN
   ▲                                  │
   │                                  │
   └──(successes > threshold)─── HALF_OPEN
                                      │
                                  (timeout)
```

**Configuration:**
- Failure threshold: 5
- Success threshold: 3
- Timeout: 30 seconds

### Retry with Backoff

```
Attempt 1: Immediate
Attempt 2: Wait 1s + jitter
Attempt 3: Wait 2s + jitter
Attempt 4: Wait 4s + jitter
Max delay: 60s
```

### Fallback Chain

```
1. Primary service
2. Cached response
3. Degraded response
4. Error message
```

---

## Observability

### Distributed Tracing

```
Request → Router Span
             │
             └──► Research Span
                      │
                      ├──► RAG Span
                      ├──► Wikipedia Span
                      └──► Weather Span
                               │
                               └──► Analysis Span
                                         │
                                         └──► Synthesis Span
                                                   │
                                                   └──► Response Span
```

### Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | Request latency |
| `agent_execution_duration_seconds` | Histogram | Agent timing |
| `rag_documents_retrieved_total` | Counter | RAG retrievals |
| `llm_tokens_total` | Counter | Token usage |

### Logging

Structured JSON logs with:
- Request ID for correlation
- User ID (if authenticated)
- Trace ID (for distributed tracing)
- Latency measurements
- Error details with stack traces

---

## Deployment Architecture

### Production (Recommended)

```
┌─────────────────────────────────────────────────────────────┐
│                    Cloudflare CDN                            │
│                         │                                    │
│    ┌────────────────────┼────────────────────┐              │
│    │                    │                    │              │
│    ▼                    ▼                    ▼              │
│ ┌──────────┐     ┌──────────┐         ┌──────────┐         │
│ │ Frontend │     │ API Pod 1│         │ API Pod 2│         │
│ │(CF Pages)│     │ (HF Space)│        │ (HF Space)│        │
│ └──────────┘     └────┬─────┘         └────┬─────┘         │
│                       │                     │               │
│                       └─────────┬───────────┘               │
│                                 │                           │
│                    ┌────────────┼────────────┐              │
│                    │            │            │              │
│                    ▼            ▼            ▼              │
│              ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│              │ Supabase │ │ Upstash  │ │  Axiom   │        │
│              │ (DB+Auth)│ │ (Redis)  │ │ (Logs)   │        │
│              └──────────┘ └──────────┘ └──────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Development

```bash
# Backend
cd backend
python -m venv .venv
.venv/Scripts/activate  # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## Performance Considerations

### Response Time Budget

| Component | Target | Max |
|-----------|--------|-----|
| Router | 50ms | 100ms |
| Research | 500ms | 1000ms |
| Analysis | 200ms | 400ms |
| Synthesis | 300ms | 600ms |
| Reflection | 200ms | 400ms |
| Response | 50ms | 100ms |
| **Total** | **1300ms** | **2600ms** |

### Optimization Strategies

1. **Parallel Data Fetching**
   - RAG, Wikipedia, Weather fetched concurrently

2. **Caching**
   - Embeddings cached in Redis
   - Search results cached (5 min TTL)

3. **Streaming**
   - SSE for immediate feedback
   - Agent status updates in real-time

4. **Connection Pooling**
   - HTTP connection reuse
   - Database connection pooling

---

## Scaling Strategy

### Horizontal Scaling

1. **Stateless API**
   - Session state in Redis
   - No local file dependencies

2. **Load Balancing**
   - Cloudflare for frontend
   - HuggingFace Spaces (auto-scaling)

3. **Database**
   - Supabase handles scaling
   - Read replicas for high load

### Vertical Limits

| Resource | Free Tier | Paid Tier |
|----------|-----------|-----------|
| Groq | 30 req/min | 1000+ req/min |
| Supabase | 500MB | 8GB+ |
| HuggingFace | 2 vCPU | 8 vCPU |

---

## Future Roadmap

1. **WebSocket Support** - Full duplex communication
2. **Multi-model Routing** - Choose LLM per query type
3. **Knowledge Graphs** - Entity relationship extraction
4. **Semantic Cache** - LLM response caching
5. **Plugin System** - Custom data sources
6. **Kubernetes Deployment** - Full container orchestration
