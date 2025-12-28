"""Reflection Agent - Self-critiques and improves responses."""

import time
from typing import Dict

from app.agents.state import AgentState
from app.services.llm import llm_service


REFLECTION_PROMPT = """You are a critical reviewer. Analyze this response and improve it.

Original Query: {query}

Draft Response: {response}

Sources Available: {sources}

Review for:
1. Accuracy - Are claims supported by the sources?
2. Completeness - Does it fully answer the query?
3. Clarity - Is it easy to understand?
4. Citations - Are sources properly referenced?

If the response is good, return it with minor polish.
If it has issues, rewrite it to fix them.

Provide the improved response (no meta-commentary, just the response):"""


async def reflection_agent(state: AgentState) -> Dict:
    """
    Reflection Agent: Reviews and improves the synthesized response.

    Updates:
        - synthesized_response (improved version)
        - agent_trace
    """
    start_time = time.time()

    draft_response = state.get("synthesized_response", "")

    # Skip if no response to reflect on
    if not draft_response:
        return {
            "agent_trace": state["agent_trace"] + [{
                "agent": "reflection",
                "action": "skipped",
                "reason": "no_draft",
                "latency_ms": 0
            }]
        }

    # Format sources for context
    sources = state.get("sources", [])
    sources_str = "\n".join([
        f"[{s.get('id', i+1)}] {s.get('title', 'Unknown')}: {s.get('snippet', '')[:100]}"
        for i, s in enumerate(sources)
    ]) or "No sources available"

    prompt = REFLECTION_PROMPT.format(
        query=state["query"],
        response=draft_response,
        sources=sources_str
    )

    # Get improved response
    improved_response = await llm_service.generate(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        temperature=0.5,
        max_tokens=2000
    )

    latency_ms = int((time.time() - start_time) * 1000)

    # Calculate improvement metrics
    original_len = len(draft_response)
    improved_len = len(improved_response)

    return {
        "synthesized_response": improved_response,
        "agent_trace": state["agent_trace"] + [{
            "agent": "reflection",
            "action": "improved",
            "original_length": original_len,
            "improved_length": improved_len,
            "latency_ms": latency_ms
        }]
    }
