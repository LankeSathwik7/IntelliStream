"""Research Agent - Retrieves relevant context from knowledge base, web, and APIs."""

import re
import time
from typing import Dict, List, Optional, Tuple

from langchain_core.messages import BaseMessage

from app.agents.state import AgentState
from app.rag.retriever import retriever
from app.services.web_search import web_search_service
from app.services.web_scraper import web_scraper_service
from app.services.wikipedia import wikipedia_service
from app.services.arxiv import arxiv_service
from app.services.external_data import news_service, weather_service, stock_service


def _extract_urls(text: str) -> List[str]:
    """Extract URLs from text."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return re.findall(url_pattern, text)


def _get_topic_from_history(messages: List[BaseMessage]) -> Optional[str]:
    """Check conversation history to determine the ongoing topic."""
    # Check recent messages for realtime data topics
    recent = messages[-6:] if len(messages) > 6 else messages
    for msg in recent:
        content = msg.content if hasattr(msg, "content") else str(msg)
        content_lower = content.lower()

        if any(kw in content_lower for kw in ["weather", "temperature", "forecast"]):
            return "weather"
        if any(kw in content_lower for kw in ["news", "headlines", "breaking"]):
            return "news"
        if any(kw in content_lower for kw in ["stock", "price", "$", "market"]):
            return "stock"

    return None


def _extract_location_from_followup(query: str) -> Optional[str]:
    """Extract a location/city from a follow-up query."""
    query_lower = query.lower().strip()

    # Check explicit patterns first (before generic location extraction)

    # Pattern: "how about <city>" or "what about <city>"
    match = re.search(r"(?:how|what) about\s+(.+?)(?:\?|$)", query_lower)
    if match:
        return match.group(1).strip().title()

    # Pattern: "i want in <city>" or "i want for <city>"
    match = re.search(r"i want\s+(?:in|for|at)\s+(.+?)(?:\?|$)", query_lower)
    if match:
        return match.group(1).strip().title()

    # Pattern: "try <city>" or "check <city>" or "in <city>"
    match = re.search(r"(?:try|check|in|for)\s+(.+?)(?:\?|$)", query_lower)
    if match:
        location = match.group(1).strip()
        # Make sure it's not a common phrase
        if location and len(location) > 2 and location not in ["the", "me", "it"]:
            return location.title()

    # Fallback: just a location name like "dekalb illinois" or "chicago"
    # Only if it's 1-3 words and doesn't contain skip words
    skip_words = ["weather", "news", "stock", "tell", "show", "give", "get", "me", "the", "please", "want", "how", "what", "about"]
    words = query_lower.split()
    if len(words) <= 3 and not any(word in skip_words for word in words):
        return query.strip().title()

    return None


def _is_research_query(text: str) -> bool:
    """Check if query is research/academic related."""
    research_keywords = [
        "research", "paper", "study", "academic", "scientific",
        "arxiv", "journal", "publication", "algorithm", "theory",
        "machine learning", "deep learning", "neural network",
        "transformer", "llm", "gpt", "bert", "model architecture"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in research_keywords)


def _is_factual_query(text: str) -> bool:
    """Check if query needs factual/encyclopedic information."""
    factual_keywords = [
        "what is", "who is", "define", "explain", "history of",
        "how does", "why does", "when did", "where is",
        "meaning of", "definition", "overview", "introduction"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in factual_keywords)


def _is_weather_query(text: str) -> bool:
    """Check if query is weather-related."""
    weather_keywords = [
        "weather", "temperature", "forecast", "rain", "sunny",
        "cloudy", "humidity", "wind", "storm", "snow", "hot", "cold", "climate"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in weather_keywords)


def _is_news_query(text: str) -> bool:
    """Check if query is news-related."""
    news_keywords = [
        "news", "latest", "headlines", "breaking", "current events",
        "today", "recent", "update", "happening"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in news_keywords)


def _is_stock_query(text: str) -> bool:
    """Check if query is stock/finance-related."""
    stock_keywords = [
        "stock", "share", "price", "ticker", "market",
        "nasdaq", "nyse", "trading", "invest", "$"
    ]
    stock_tickers = ["aapl", "googl", "msft", "amzn", "tsla", "nvda", "meta"]
    text_lower = text.lower()
    has_keyword = any(keyword in text_lower for keyword in stock_keywords)
    has_ticker = any(ticker in text_lower for ticker in stock_tickers)
    return has_keyword or has_ticker


def _extract_city(text: str) -> str:
    """Extract city name from weather query."""
    # Common city names to look for (expanded list)
    known_cities = [
        # US Major cities
        "new york", "los angeles", "chicago", "houston", "phoenix",
        "philadelphia", "san antonio", "san diego", "dallas", "san jose",
        "austin", "jacksonville", "fort worth", "columbus", "charlotte",
        "seattle", "denver", "washington", "boston", "nashville",
        "detroit", "portland", "las vegas", "memphis", "louisville",
        "baltimore", "milwaukee", "albuquerque", "tucson", "fresno",
        "sacramento", "kansas city", "atlanta", "miami", "oakland",
        "minneapolis", "cleveland", "tampa", "st louis", "pittsburgh",
        # Illinois cities
        "dekalb", "naperville", "aurora", "rockford", "joliet", "springfield",
        "peoria", "champaign", "urbana", "bloomington", "decatur", "evanston",
        # International
        "london", "paris", "tokyo", "sydney", "mumbai", "delhi",
        "berlin", "madrid", "rome", "amsterdam", "toronto", "vancouver",
        "singapore", "hong kong", "dubai", "beijing", "shanghai",
        "moscow", "istanbul", "cairo", "lagos", "nairobi", "seoul",
        "bangkok", "jakarta", "manila", "kuala lumpur", "ho chi minh"
    ]
    text_lower = text.lower()

    # First try to find known cities
    for city in known_cities:
        if city in text_lower:
            return city.title()

    # Try to extract city after "in" or "for"
    patterns = [
        r"weather (?:in|for|at) ([a-zA-Z\s,]+?)(?:\?|$|today|tomorrow)",
        r"(?:in|for|at) ([a-zA-Z\s,]+?)(?:\?|$|weather)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            city = match.group(1).strip()
            # Validate it's not a common word
            common_words = ["the", "me", "my", "current", "today", "now", "a", "an", "this", "that"]
            if city and len(city) > 2 and city not in common_words:
                return city.title()

    # Pattern: "<city> weather" - but only if it's a reasonable city name (not common phrases)
    match = re.search(r"^([a-zA-Z\s,]+?) weather", text_lower)
    if match:
        city = match.group(1).strip()
        # Must be short (1-3 words) and not contain common verbs/phrases
        words = city.split()
        skip_words = ["tell", "me", "the", "show", "get", "give", "what", "is", "my"]
        if 1 <= len(words) <= 3 and not any(w in skip_words for w in words):
            return city.title()

    return "New York"


def _extract_stock_symbol(text: str) -> str:
    """Extract stock symbol from query."""
    text_upper = text.upper()
    known_symbols = ["AAPL", "GOOGL", "GOOG", "MSFT", "AMZN", "TSLA", "NVDA", "META", "NFLX"]
    for symbol in known_symbols:
        if symbol in text_upper:
            return symbol
    # Try to find $ followed by letters
    match = re.search(r'\$([A-Za-z]+)', text)
    if match:
        return match.group(1).upper()
    return ""


async def research_agent(state: AgentState) -> Dict:
    """
    Research Agent: Retrieves relevant documents using RAG + Web + Wikipedia + ArXiv.
    Now context-aware - understands follow-up queries.

    Strategy:
    1. First check if user provided URLs to scrape
    2. Search local documents (RAG)
    3. If factual query, search Wikipedia
    4. If research query, search ArXiv
    5. If results are insufficient, search the web

    Updates:
        - retrieved_documents
        - context
        - sources
        - agent_trace
    """
    start_time = time.time()
    query = state["query"]
    messages = state.get("messages", [])

    all_documents = []
    actions = []

    # Check if this is a follow-up to a previous topic
    history_topic = _get_topic_from_history(messages) if messages else None
    followup_location = _extract_location_from_followup(query) if history_topic else None

    # Step 1: Check for URLs to scrape
    urls = _extract_urls(query)
    if urls:
        scraped = await web_scraper_service.scrape_multiple(urls[:3])
        for doc in scraped:
            if doc.get("success") and doc.get("content"):
                all_documents.append({
                    "id": doc["url"],
                    "title": doc.get("title", "Web Page"),
                    "content": doc["content"],
                    "source_url": doc["url"],
                    "score": 0.9
                })
        actions.append(f"scraped_{len([d for d in scraped if d.get('success')])}_urls")

    # Determine query type for smart filtering
    is_weather = _is_weather_query(query) or history_topic == "weather"
    is_news = _is_news_query(query) or history_topic == "news"
    is_stock = _is_stock_query(query) or history_topic == "stock"
    is_realtime_query = is_weather or is_news or is_stock

    # Step 2: Search local documents (RAG)
    # Always search, but filter results smartly for realtime queries
    documents, _ = await retriever.retrieve_with_context(
        query=query,
        top_k=5,
        context_window=500,
    )

    # Smart filtering: for realtime queries, only include documents that are actually relevant
    rag_count = 0
    for doc in documents:
        score = doc.get("score", 0)
        content_lower = doc.get("content", "").lower()
        title_lower = doc.get("title", "").lower()

        # Higher threshold for realtime queries to filter out irrelevant docs
        min_score = 0.5 if is_realtime_query else 0.3

        if score < min_score:
            continue

        # For realtime queries, check if document is actually about that topic
        if is_realtime_query:
            is_relevant = False
            if is_weather:
                weather_terms = ["weather", "temperature", "climate", "forecast", "rain", "humidity", "wind"]
                is_relevant = any(term in content_lower or term in title_lower for term in weather_terms)
            elif is_news:
                news_terms = ["news", "article", "headline", "report", "breaking"]
                is_relevant = any(term in content_lower or term in title_lower for term in news_terms)
            elif is_stock:
                stock_terms = ["stock", "price", "market", "trading", "share", "investor"]
                is_relevant = any(term in content_lower or term in title_lower for term in stock_terms)

            if not is_relevant:
                continue  # Skip irrelevant documents for realtime queries

        all_documents.append(doc)
        rag_count += 1

    actions.append(f"rag_{rag_count}_docs" + ("_filtered" if is_realtime_query else ""))

    # Step 3: If factual query, search Wikipedia
    if _is_factual_query(query):
        try:
            wiki_results = await wikipedia_service.search_and_summarize(query, max_results=2)
            for wiki in wiki_results:
                all_documents.append({
                    "id": f"wiki_{wiki.get('title', '')}",
                    "title": f"Wikipedia: {wiki.get('title', '')}",
                    "content": wiki.get("content", ""),
                    "source_url": wiki.get("url"),
                    "score": wiki.get("score", 0.8)
                })
            actions.append(f"wiki_{len(wiki_results)}_articles")
        except Exception as e:
            print(f"Wikipedia search error: {e}")

    # Step 4: If research query, search ArXiv
    if _is_research_query(query):
        try:
            arxiv_results = await arxiv_service.search(query, max_results=3)
            formatted_papers = arxiv_service.format_for_rag(arxiv_results)
            for paper in formatted_papers:
                all_documents.append({
                    "id": paper.get("id", ""),
                    "title": f"ArXiv: {paper.get('title', '')}",
                    "content": paper.get("content", ""),
                    "source_url": paper.get("source_url"),
                    "score": paper.get("score", 0.85)
                })
            actions.append(f"arxiv_{len(arxiv_results)}_papers")
        except Exception as e:
            print(f"ArXiv search error: {e}")

    # Step 5: If weather query OR follow-up to weather, get weather data
    is_weather = _is_weather_query(query) or (history_topic == "weather" and bool(followup_location))
    if is_weather and weather_service.is_configured():
        try:
            # Use follow-up location if detected, otherwise extract from query
            city = followup_location if followup_location else _extract_city(query)
            weather = await weather_service.get_current_weather(city)
            if weather:
                weather_content = (
                    f"Current weather in {weather['city']}, {weather['country']}:\n"
                    f"Temperature: {weather['temperature']}°C (feels like {weather['feels_like']}°C)\n"
                    f"Conditions: {weather['description']}\n"
                    f"Humidity: {weather['humidity']}%\n"
                    f"Wind: {weather['wind_speed']} m/s"
                )
                all_documents.append({
                    "id": f"weather_{city}",
                    "title": f"Weather: {weather['city']}",
                    "content": weather_content,
                    "source_url": "https://openweathermap.org",
                    "score": 0.95
                })
                actions.append("weather_live")
        except Exception as e:
            print(f"Weather API error: {e}")

    # Step 6: If news query OR follow-up to news, get latest news
    is_news = _is_news_query(query) or history_topic == "news"
    if is_news and news_service.is_configured():
        try:
            # Use context for better search if it's a follow-up
            search_query = query if _is_news_query(query) else f"latest news {query}"
            news_results = await news_service.search_news(search_query, max_results=3)
            for article in news_results:
                all_documents.append({
                    "id": article.get("url", ""),
                    "title": f"News: {article.get('title', '')}",
                    "content": article.get("description", "") or article.get("content", ""),
                    "source_url": article.get("url"),
                    "score": 0.85
                })
            actions.append(f"news_{len(news_results)}_articles")
        except Exception as e:
            print(f"News API error: {e}")

    # Step 7: If stock query OR follow-up to stock, get stock data
    is_stock = _is_stock_query(query) or history_topic == "stock"
    if is_stock and stock_service.is_configured():
        try:
            symbol = _extract_stock_symbol(query)
            # If no symbol in current query but it's a follow-up, try to extract from history
            if not symbol and history_topic == "stock":
                for msg in reversed(messages[-6:] if len(messages) > 6 else messages):
                    content = msg.content if hasattr(msg, "content") else str(msg)
                    symbol = _extract_stock_symbol(content)
                    if symbol:
                        break
            if symbol:
                quote = await stock_service.get_quote(symbol)
                if quote:
                    stock_content = (
                        f"Stock: {quote['symbol']}\n"
                        f"Price: ${quote['price']}\n"
                        f"Change: {quote['change']} ({quote['change_percent']})\n"
                        f"Volume: {quote['volume']}\n"
                        f"High: ${quote['high']} | Low: ${quote['low']}"
                    )
                    all_documents.append({
                        "id": f"stock_{symbol}",
                        "title": f"Stock Quote: {symbol}",
                        "content": stock_content,
                        "source_url": f"https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol={symbol}",
                        "score": 0.95
                    })
                    actions.append(f"stock_{symbol}")
        except Exception as e:
            print(f"Stock API error: {e}")

    # Step 8: If results are insufficient, search the web
    if len(all_documents) < 3 and web_search_service.is_configured():
        web_results = await web_search_service.search(query, max_results=5)

        for result in web_results:
            if not result.get("is_summary"):
                all_documents.append({
                    "id": result.get("url", f"web_{len(all_documents)}"),
                    "title": result.get("title", "Web Result"),
                    "content": result.get("content", ""),
                    "source_url": result.get("url"),
                    "score": result.get("score", 0.5)
                })

        actions.append(f"web_{len(web_results)}_results")

    # Sort documents by score (highest first) to prioritize real-time data
    all_documents.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_docs = all_documents[:10]  # Take top 10 documents

    # Build context string
    if top_docs:
        context_parts = []
        for i, doc in enumerate(top_docs, 1):
            content = doc["content"]
            if len(content) > 500:
                content = content[:500] + "..."
            context_parts.append(f"[{i}] {doc['title']}\n{content}")
        context = "\n\n---\n\n".join(context_parts)
    else:
        context = "No relevant documents found."

    # Format sources for citation
    sources = [
        {
            "id": f"[{i+1}]",
            "title": doc["title"],
            "url": doc.get("source_url"),
            "snippet": doc["content"][:150] + "..."
            if len(doc["content"]) > 150
            else doc["content"],
            "score": doc.get("score", 0),
        }
        for i, doc in enumerate(top_docs)
    ]

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "retrieved_documents": top_docs,
        "context": context,
        "sources": sources,
        "agent_trace": state["agent_trace"]
        + [
            {
                "agent": "research",
                "action": "+".join(actions) if actions else "retrieved",
                "documents_found": len(all_documents),
                "latency_ms": latency_ms,
            }
        ],
    }
