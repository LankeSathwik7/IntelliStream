"""Router Agent - Classifies queries and determines workflow path."""

import re
import time
from typing import Dict, List, Literal

from langchain_core.messages import BaseMessage

from app.agents.state import AgentState
from app.services.llm import llm_service


def _contains_url(text: str) -> bool:
    """Check if text contains a URL."""
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    return bool(re.search(url_pattern, text))


REALTIME_KEYWORDS = [
    # Weather
    "weather", "temperature", "forecast", "rain", "sunny", "cloudy", "climate",
    # News
    "news", "headlines", "breaking", "latest news", "current events",
    # Stocks
    "stock", "share price", "ticker", "$aapl", "$googl", "$msft", "$tsla", "$nvda",
    "stock price", "market"
]


def _needs_realtime_data(text: str) -> bool:
    """Check if query needs real-time data (weather, news, stocks)."""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in REALTIME_KEYWORDS)


def _is_ambiguous_query(text: str) -> bool:
    """
    Check if query is too vague and needs clarification.
    Examples: "tell me about dekalb", "what about chicago", "information on paris"
    """
    text_lower = text.lower().strip()

    # Patterns that are ambiguous without more context
    ambiguous_patterns = [
        r"^tell me about\s+[a-z\s,]+$",  # "tell me about dekalb"
        r"^(what|how) about\s+[a-z\s,]+$",  # "what about chicago"
        r"^information (on|about)\s+[a-z\s,]+$",  # "information on paris"
        r"^describe\s+[a-z\s,]+$",  # "describe new york"
        r"^explain\s+[a-z\s,]+$",  # "explain quantum"
        r"^details (on|about)\s+[a-z\s,]+$",  # "details on tokyo"
    ]

    for pattern in ambiguous_patterns:
        if re.match(pattern, text_lower):
            # Check if it contains specific topic keywords - if so, not ambiguous
            specific_topics = [
                "weather", "temperature", "forecast", "climate",
                "news", "headlines", "events",
                "stock", "price", "market",
                "history", "population", "economy", "geography",
                "food", "culture", "tourism", "hotels"
            ]
            if any(topic in text_lower for topic in specific_topics):
                return False
            return True

    return False


def _get_conversation_context(messages: List[BaseMessage]) -> str:
    """Extract recent conversation context for routing decisions."""
    # Get last 4 messages for context
    recent = messages[-4:] if len(messages) > 4 else messages
    context_parts = []
    for msg in recent:
        role = "User" if hasattr(msg, "type") and msg.type == "human" else "Assistant"
        content = msg.content if hasattr(msg, "content") else str(msg)
        # Truncate long messages
        if len(content) > 200:
            content = content[:200] + "..."
        context_parts.append(f"{role}: {content}")
    return "\n".join(context_parts)


def _is_followup_to_realtime(query: str, messages: List[BaseMessage]) -> bool:
    """Check if this query is a follow-up to a realtime data request."""
    # Check if any recent message (last 3 exchanges) mentioned realtime topics
    recent = messages[-6:] if len(messages) > 6 else messages
    has_realtime_history = False
    for msg in recent:
        content = msg.content if hasattr(msg, "content") else str(msg)
        if _needs_realtime_data(content):
            has_realtime_history = True
            break

    # Only consider follow-up patterns if there's actual realtime history
    if not has_realtime_history:
        return False

    # Check for location-like patterns that suggest follow-up
    location_patterns = [
        r"\bi want\b.*\b(in|for|at)\b",  # "i want in dekalb"
        r"\b(how about|what about)\b",    # "how about chicago"
        r"\b(try|check|get)\b.*\b(for|in)\b",  # "try for new york"
    ]
    query_lower = query.lower().strip()
    for pattern in location_patterns:
        if re.search(pattern, query_lower):
            return True

    # Check if it's just a short location name (1-3 words, no common verbs)
    words = query_lower.split()
    skip_words = ["tell", "me", "about", "the", "what", "is", "are", "show", "give", "get"]
    if len(words) <= 3 and not any(w in skip_words for w in words):
        return True

    return False

ROUTER_PROMPT = """You are a query router for an intelligence system. Analyze the user's query and determine the best path to answer it.

Categories:
1. RESEARCH - The query requires searching documents, retrieving context, or finding specific information
2. DIRECT - The query can be answered directly without searching (greetings, simple factual questions, clarifications)
3. CLARIFY - The query is too vague or ambiguous to answer properly

User Query: {query}

Respond with ONLY one word: RESEARCH, DIRECT, or CLARIFY"""


CONTEXT_AWARE_ROUTER_PROMPT = """You are a query router for an intelligence system. Analyze the user's query IN CONTEXT of the conversation and determine the best path.

Recent Conversation:
{context}

Current Query: {query}

Categories:
1. RESEARCH - The query requires searching documents, real-time data (weather/news/stocks), or finding specific information. Also use this if the query is a follow-up to a previous research topic (e.g., asking about a different location after asking about weather).
2. DIRECT - The query can be answered directly without searching (greetings, simple factual questions, general clarifications)
3. CLARIFY - The query is too vague or ambiguous to answer properly

Respond with ONLY one word: RESEARCH, DIRECT, or CLARIFY"""


async def router_agent(state: AgentState) -> Dict:
    """
    Router Agent: Classifies the query and determines routing.
    Now context-aware - checks conversation history for follow-up queries.

    Updates:
        - route_decision
        - needs_clarification
        - clarification_question
        - agent_trace
    """
    start_time = time.time()
    query = state["query"]
    messages = state.get("messages", [])

    # Force research routing if query contains URLs (for web scraping)
    if _contains_url(query):
        route = "research"
        needs_clarification = False
        clarification_question = None
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "route_decision": route,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "agent_trace": state["agent_trace"]
            + [
                {
                    "agent": "router",
                    "action": "classified",
                    "decision": route,
                    "reason": "url_detected",
                    "latency_ms": latency_ms,
                }
            ],
        }

    # Force research routing for real-time data queries (weather, news, stocks)
    if _needs_realtime_data(query):
        route = "research"
        needs_clarification = False
        clarification_question = None
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "route_decision": route,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "agent_trace": state["agent_trace"]
            + [
                {
                    "agent": "router",
                    "action": "classified",
                    "decision": route,
                    "reason": "realtime_data",
                    "latency_ms": latency_ms,
                }
            ],
        }

    # Check if this is a follow-up to a realtime data query
    if messages and _is_followup_to_realtime(query, messages):
        route = "research"
        needs_clarification = False
        clarification_question = None
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "route_decision": route,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "agent_trace": state["agent_trace"]
            + [
                {
                    "agent": "router",
                    "action": "classified",
                    "decision": route,
                    "reason": "realtime_followup",
                    "latency_ms": latency_ms,
                }
            ],
        }

    # Check for ambiguous queries that need clarification
    if _is_ambiguous_query(query):
        route = "clarify"
        needs_clarification = True
        clarification_question = await _generate_clarification(query)
        latency_ms = int((time.time() - start_time) * 1000)

        return {
            "route_decision": route,
            "needs_clarification": needs_clarification,
            "clarification_question": clarification_question,
            "agent_trace": state["agent_trace"]
            + [
                {
                    "agent": "router",
                    "action": "classified",
                    "decision": route,
                    "reason": "ambiguous_query",
                    "latency_ms": latency_ms,
                }
            ],
        }

    # Get routing decision from LLM (use context-aware prompt if we have history)
    if messages and len(messages) > 1:
        context = _get_conversation_context(messages[:-1])  # Exclude current query
        decision = await llm_service.generate(
            messages=[{
                "role": "user",
                "content": CONTEXT_AWARE_ROUTER_PROMPT.format(context=context, query=query)
            }],
            model="llama-3.1-8b-instant",
            max_tokens=10,
        )
    else:
        decision = await llm_service.route_query(query)

    # Parse decision
    route = "research"  # default
    needs_clarification = False
    clarification_question = None

    if "DIRECT" in decision.upper():
        route = "direct"
    elif "CLARIFY" in decision.upper():
        route = "clarify"
        needs_clarification = True
        # Generate clarification question
        clarification_question = await _generate_clarification(query)
    else:
        route = "research"

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "route_decision": route,
        "needs_clarification": needs_clarification,
        "clarification_question": clarification_question,
        "agent_trace": state["agent_trace"]
        + [
            {
                "agent": "router",
                "action": "classified",
                "decision": route,
                "latency_ms": latency_ms,
            }
        ],
    }


async def _generate_clarification(query: str) -> str:
    """Generate a clarification question for ambiguous queries."""
    prompt = f"""The following query is ambiguous and needs clarification.
Generate a short, helpful question to clarify what the user wants.

Query: {query}

Clarification question:"""

    return await llm_service.generate(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.1-8b-instant",
        max_tokens=100,
    )


def route_decision(state: AgentState) -> Literal["research", "direct", "clarify"]:
    """Routing function for conditional edges."""
    decision = state.get("route_decision", "research")
    if decision == "direct":
        return "direct"
    elif decision == "clarify":
        return "clarify"
    return "research"
