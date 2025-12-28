"""Agent state definitions for LangGraph workflow."""

from typing import Annotated, Any, Dict, List, Optional, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State that flows through the agent workflow.

    This is the central data structure that each agent reads from
    and writes to as the workflow progresses.
    """

    # ================
    # INPUT
    # ================

    # The original user query
    query: str

    # Conversation thread ID
    thread_id: str

    # User ID (from auth)
    user_id: Optional[str]

    # Conversation history
    messages: Annotated[List[BaseMessage], add_messages]

    # ================
    # AGENT DECISIONS
    # ================

    # Router decision: "research" | "direct" | "clarify"
    route_decision: str

    # Whether the query needs clarification
    needs_clarification: bool

    # Clarification question (if needs_clarification)
    clarification_question: Optional[str]

    # ================
    # RESEARCH RESULTS
    # ================

    # Retrieved documents from RAG
    retrieved_documents: List[Dict[str, Any]]

    # Formatted context string for LLM
    context: str

    # ================
    # ANALYSIS RESULTS
    # ================

    # Extracted entities
    entities: List[Dict[str, str]]

    # Sentiment analysis
    sentiment: Optional[Dict[str, Any]]

    # Key facts extracted
    key_facts: List[str]

    # ================
    # SYNTHESIS RESULTS
    # ================

    # Synthesized insight
    synthesized_response: str

    # ================
    # FINAL OUTPUT
    # ================

    # Final response to user
    final_response: str

    # Sources used (for citations)
    sources: List[Dict[str, Any]]

    # ================
    # OBSERVABILITY
    # ================

    # Agent execution trace
    agent_trace: List[Dict[str, Any]]

    # Total tokens used
    total_tokens: int

    # Total latency in ms
    total_latency_ms: int

    # Any errors
    error: Optional[str]


def create_initial_state(
    query: str,
    thread_id: str,
    user_id: Optional[str] = None,
    messages: Optional[List[BaseMessage]] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> AgentState:
    """Create initial state for a new query."""
    from langchain_core.messages import HumanMessage, AIMessage

    # Build messages from history if provided
    msg_list = messages or []
    if history:
        for msg in history:
            if msg.get("role") == "user":
                msg_list.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                msg_list.append(AIMessage(content=msg.get("content", "")))

    # Add current query as the latest message
    msg_list.append(HumanMessage(content=query))

    return AgentState(
        query=query,
        thread_id=thread_id,
        user_id=user_id,
        messages=msg_list,
        route_decision="",
        needs_clarification=False,
        clarification_question=None,
        retrieved_documents=[],
        context="",
        entities=[],
        sentiment=None,
        key_facts=[],
        synthesized_response="",
        final_response="",
        sources=[],
        agent_trace=[],
        total_tokens=0,
        total_latency_ms=0,
        error=None,
    )
