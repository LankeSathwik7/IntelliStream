---
title: IntelliStream API
emoji: 🧠
colorFrom: blue
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# IntelliStream API

Real-Time Agentic RAG Intelligence Platform with a 6-agent LangGraph workflow.

## Features

- **6-Agent LangGraph Workflow**: Router → Research → Analysis → Synthesis → Reflection → Response
- **Multi-Modal Support**: Image understanding (Groq Vision), Audio transcription (Whisper), PDF parsing
- **Real-Time Data**: Wikipedia, ArXiv, NewsAPI, OpenWeatherMap, Alpha Vantage
- **Vector Search**: Voyage AI embeddings with Supabase pgvector
- **Authentication**: Supabase Auth with per-user conversation history
- **Observability**: Axiom monitoring and metrics

## API Endpoints

- `GET /health` - Health check
- `POST /api/chat` - Chat endpoint with streaming
- `POST /api/documents/upload` - Upload documents
- `GET /api/documents` - List documents

## Environment Variables

Required:
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_SERVICE_ROLE_KEY` - Supabase service role key
- `GROQ_API_KEY` - Groq API key for LLM
- `VOYAGE_API_KEY` - Voyage AI API key for embeddings

Optional:
- `UPSTASH_REDIS_REST_URL` - Upstash Redis URL for rate limiting
- `UPSTASH_REDIS_REST_TOKEN` - Upstash Redis token
- `AXIOM_TOKEN` - Axiom API token for monitoring
- `NEWSAPI_KEY` - NewsAPI key
- `OPENWEATHER_API_KEY` - OpenWeatherMap API key
- `ALPHAVANTAGE_API_KEY` - Alpha Vantage API key
