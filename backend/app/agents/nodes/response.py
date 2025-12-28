"""Response Agent - Formats final output with citations."""

import time
from typing import AsyncGenerator, Dict

from app.agents.state import AgentState
from app.services.llm import llm_service


async def response_agent(state: AgentState) -> Dict:
    """
    Response Agent: Formats the final response.

    Updates:
        - final_response
        - total_latency_ms
        - agent_trace
    """
    start_time = time.time()

    # Use synthesized response if available, otherwise generate direct response
    if state.get("synthesized_response"):
        final_response = state["synthesized_response"]
    elif state.get("route_decision") == "direct":
        # Direct response without research - include conversation history
        conversation_messages = []
        for msg in state.get("messages", []):
            if hasattr(msg, "type"):
                role = "user" if msg.type == "human" else "assistant"
                conversation_messages.append({"role": role, "content": msg.content})

        # If no history built from state, just use the query
        if not conversation_messages:
            conversation_messages = [{"role": "user", "content": state["query"]}]

        final_response = await llm_service.generate(
            messages=conversation_messages,
            temperature=0.7,
        )
    elif state.get("needs_clarification"):
        final_response = state.get(
            "clarification_question", "Could you please clarify your question?"
        )
    else:
        final_response = "I couldn't find relevant information to answer your query."

    latency_ms = int((time.time() - start_time) * 1000)

    # Calculate total latency
    total_latency = (
        sum(t.get("latency_ms", 0) for t in state.get("agent_trace", [])) + latency_ms
    )

    return {
        "final_response": final_response,
        "total_latency_ms": total_latency,
        "agent_trace": state["agent_trace"]
        + [
            {
                "agent": "response",
                "action": "formatted",
                "response_length": len(final_response),
                "latency_ms": latency_ms,
            }
        ],
    }


async def response_agent_stream(state: AgentState) -> AsyncGenerator[Dict, None]:
    """
    Streaming version of response agent.
    Yields token-by-token updates.
    """
    start_time = time.time()

    if state.get("route_decision") == "direct":
        # Stream direct response
        prompt = state["query"]
        system = None
    else:
        # Stream synthesis-style response
        prompt = f"""Based on this context and analysis, provide a comprehensive answer.

Query: {state['query']}

Context: {state.get('context', 'No context available')[:2000]}

Key Facts: {', '.join(state.get('key_facts', []))}

Provide a well-structured response with citations [1], [2] etc:"""
        system = (
            "You are an expert analyst providing accurate, well-cited information."
        )

    full_response = ""

    async for token in llm_service.generate_stream(
        messages=[{"role": "user", "content": prompt}],
        system_prompt=system,
    ):
        full_response += token
        yield {"type": "token", "content": token}

    latency_ms = int((time.time() - start_time) * 1000)

    yield {
        "type": "complete",
        "final_response": full_response,
        "latency_ms": latency_ms,
    }
