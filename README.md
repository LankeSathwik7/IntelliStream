# 🧠 IntelliStream

**Real-Time Agentic RAG Intelligence Platform**

A sophisticated intelligence platform powered by a 6-agent LangGraph workflow for real-time document retrieval, analysis, synthesis, and self-improvement.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         IntelliStream                                │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (Next.js 15 + Tailwind)                                   │
│  ├── Chat Interface with SSE streaming                              │
│  ├── Agent status visualization                                     │
│  ├── Source citations display                                       │
│  ├── User authentication (Supabase Auth)                            │
│  └── Per-user conversation history                                  │
├─────────────────────────────────────────────────────────────────────┤
│  Backend API (FastAPI)                                              │
│  ├── /api/chat - Chat with streaming                                │
│  ├── /api/documents - Document management (PDF, DOCX, TXT)          │
│  ├── /api/settings - User settings                                  │
│  └── /health - Health checks                                        │
├─────────────────────────────────────────────────────────────────────┤
│  6-Agent LangGraph Workflow                                         │
│                                                                     │
│  Router ──► Research ──► Analysis ──► Synthesis ──► Reflection      │
│    │                                                    │           │
│    │ (direct/clarify)                                   ▼           │
│    └────────────────────────────────────────────► Response          │
├─────────────────────────────────────────────────────────────────────┤
│  Real-Time Data Sources                                             │
│  ├── Wikipedia API (Encyclopedia)                                   │
│  ├── ArXiv API (Research papers)                                    │
│  ├── Tavily (Web search)                                            │
│  ├── NewsAPI (Latest news)                                          │
│  ├── OpenWeatherMap (Live weather)                                  │
│  └── Alpha Vantage (Stock quotes)                                   │
├─────────────────────────────────────────────────────────────────────┤
│  Services                                                           │
│  ├── Supabase (Database + Auth + pgvector)                         │
│  ├── Groq (LLM - llama-3.3-70b + Whisper + Vision)                 │
│  ├── Voyage AI (Embeddings - voyage-3)                             │
│  ├── Upstash Redis (Rate limiting + Caching)                       │
│  └── Axiom (Monitoring + Logs)                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## ✨ Features

### Core Features
- **6-Agent Workflow**: Router, Research, Analysis, Synthesis, Reflection, Response
- **Hybrid RAG**: Vector + keyword search with Supabase pgvector
- **Real-time Streaming**: SSE for live agent status and token streaming
- **Smart Caching**: Redis caching for embeddings and search results
- **Entity Extraction**: Automatic entity and sentiment analysis
- **Source Citations**: Linked references with relevance scores

### Real-Time Data Integration
- **Wikipedia**: Encyclopedia lookups for factual queries
- **ArXiv**: Research paper search for academic queries
- **Web Search**: Tavily for general web search
- **Live Weather**: OpenWeatherMap for weather queries
- **Latest News**: NewsAPI for news and current events
- **Stock Quotes**: Alpha Vantage for stock price queries

### Multi-Modal Support
- **Image Understanding**: Groq Vision for image analysis
- **Audio Transcription**: Whisper for audio-to-text
- **Document Parsing**: PDF and DOCX file support

### Advanced Features
- **Self-Reflection Agent**: Improves response quality automatically
- **Conversation Memory**: Per-user chat history with threads
- **User Authentication**: Supabase Auth integration
- **Rate Limiting**: Upstash Redis for API protection
- **Monitoring**: Axiom for logs and metrics

## 🛠️ Tech Stack

| Component | Technology | Free Tier |
|-----------|------------|-----------|
| Backend | FastAPI + LangGraph | - |
| Frontend | Next.js 15 + Tailwind | - |
| Database | Supabase (PostgreSQL + pgvector) | 500MB |
| LLM | Groq (llama-3.3-70b) | 30 req/min |
| Vision | Groq (llama-3.2-90b-vision) | 30 req/min |
| Audio | Groq (whisper-large-v3) | 30 req/min |
| Embeddings | Voyage AI (voyage-3) | 200M tokens |
| Cache | Upstash Redis | 10K commands/day |
| Web Search | Tavily | 1000 searches/month |
| News | NewsAPI | 100 requests/day |
| Weather | OpenWeatherMap | 1000 calls/day |
| Stocks | Alpha Vantage | 25 requests/day |
| Monitoring | Axiom | 500GB/month |
| Backend Hosting | HuggingFace Spaces | 2 vCPU, 16GB RAM |
| Frontend Hosting | Cloudflare Pages | Unlimited |

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Supabase account
- Groq API key
- Voyage AI API key
- Upstash Redis account

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/intellistream.git
cd intellistream
```

### 2. Setup Backend

```bash
cd backend

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate
# Activate (Mac/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Setup Database

1. Create a Supabase project at https://supabase.com
2. Go to SQL Editor and run `docs/database-schema.sql`
3. Copy your credentials from Project Settings > API

### 4. Configure Environment

```bash
# Copy example env
cp .env.example .env

# Edit .env with your credentials
```

### 5. Run Backend

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

### 6. Setup Frontend

```bash
cd frontend

# Install dependencies
npm install

# Copy example env
cp .env.example .env.local

# Edit .env.local with your credentials
```

### 7. Run Frontend

```bash
npm run dev
```

Visit http://localhost:3000

## 🔐 Environment Variables

### Backend (.env)

```env
# Required: Core Services
GROQ_API_KEY=gsk_xxxxxxxxxxxx
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
VOYAGE_API_KEY=pa-xxxxxxxxxxxx
UPSTASH_REDIS_REST_URL=https://xxxxx.upstash.io
UPSTASH_REDIS_REST_TOKEN=AXxxxxxxxxxxxxx

# Optional: Real-Time APIs
TAVILY_API_KEY=tvly-xxxxxxxxxxxx
NEWSAPI_KEY=xxxxxxxxxxxx
OPENWEATHER_API_KEY=xxxxxxxxxxxx
ALPHAVANTAGE_API_KEY=xxxxxxxxxxxx

# Optional: Monitoring
AXIOM_TOKEN=xaat-xxxxxxxxxxxx
AXIOM_ORG_ID=your-org-id
AXIOM_DATASET=intellistream-logs

# App Config
ENVIRONMENT=development
DEBUG=true
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:3000
```

### Frontend (.env.local)

```env
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 📡 API Endpoints

### Chat

```bash
# Non-streaming
POST /api/chat
{
  "message": "What are the latest AI trends?",
  "thread_id": "optional-thread-id"
}

# Streaming (SSE)
POST /api/chat/stream
{
  "message": "What are the latest AI trends?"
}
```

### Documents

```bash
# List documents
GET /api/documents?limit=10&offset=0

# Create document
POST /api/documents
{
  "title": "Document Title",
  "content": "Document content...",
  "source_type": "research"
}

# Search documents
POST /api/documents/search
{
  "query": "AI trends",
  "top_k": 5
}

# Upload file (PDF, DOCX, TXT)
POST /api/documents/upload
Content-Type: multipart/form-data
file: <file>
```

### Real-Time Data Examples

```bash
# Weather query
POST /api/chat
{"message": "What's the weather in Tokyo?"}

# Stock query
POST /api/chat
{"message": "What's the current price of AAPL?"}

# News query
POST /api/chat
{"message": "What are the latest tech headlines?"}

# Research query
POST /api/chat
{"message": "What are the latest transformer architecture papers?"}
```

## ☁️ Deployment

### Backend (HuggingFace Spaces)

1. Create a Space at https://huggingface.co/spaces
2. Choose Docker SDK
3. Push your code:

```bash
git remote add hf https://huggingface.co/spaces/USERNAME/intellistream-api
git push hf main
```

4. Add secrets in Space Settings

### Frontend (Cloudflare Pages)

1. Connect GitHub repository
2. Build command: `cd frontend && npm run build`
3. Output directory: `frontend/out`
4. Add environment variables

## 📁 Project Structure

```
intellistream/
├── backend/
│   ├── app/
│   │   ├── agents/           # LangGraph agents
│   │   │   ├── nodes/        # Individual agent nodes
│   │   │   │   ├── router.py
│   │   │   │   ├── research.py
│   │   │   │   ├── analysis.py
│   │   │   │   ├── synthesizer.py
│   │   │   │   ├── reflection.py
│   │   │   │   └── response.py
│   │   │   ├── state.py      # Agent state definition
│   │   │   └── graph.py      # Workflow graph
│   │   ├── api/
│   │   │   └── routes/       # API endpoints
│   │   ├── rag/              # RAG components
│   │   │   ├── embeddings.py
│   │   │   ├── retriever.py
│   │   │   └── chunker.py
│   │   ├── services/         # External services
│   │   │   ├── supabase.py
│   │   │   ├── llm.py
│   │   │   ├── cache.py
│   │   │   ├── web_search.py
│   │   │   ├── wikipedia.py
│   │   │   ├── arxiv.py
│   │   │   └── external_data.py  # News, Weather, Stocks
│   │   ├── config.py
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── app/              # Next.js app router
│   │   ├── components/       # React components
│   │   ├── hooks/            # Custom hooks
│   │   ├── lib/              # Utilities
│   │   └── types/            # TypeScript types
│   ├── package.json
│   └── tailwind.config.ts
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md
│   └── database-schema.sql
├── .github/
│   └── workflows/
│       └── ci.yml
├── .env.example
└── README.md
```

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Made with ❤️
</p>

<p align="center">
  Built with
  <a href="https://nextjs.org">Next.js</a> •
  <a href="https://fastapi.tiangolo.com">FastAPI</a> •
  <a href="https://langchain-ai.github.io/langgraph/">LangGraph</a> •
  <a href="https://supabase.com">Supabase</a> •
  <a href="https://groq.com">Groq</a> •
  <a href="https://www.voyageai.com">Voyage AI</a>
</p>
