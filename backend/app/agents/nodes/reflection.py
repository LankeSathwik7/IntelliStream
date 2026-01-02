"""Reflection Agent - Self-critiques and improves responses."""

import time
from typing import Dict

from app.agents.state import AgentState
from app.services.llm import llm_service


REFLECTION_PROMPT = """Review and improve this response. Be strict about accuracy and conciseness.

Query: {query}

Draft Response: {response}

Available Sources:
{sources}

STRICT RULES:
1. REMOVE any citation [N] if that specific information is NOT in source [N]
2. REMOVE any fact not found in the sources - replace with "I don't have that information"
3. SHORTEN the response - match length to query complexity. Simple queries need 1-2 sentences max.
4. REMOVE unnecessary filler, preambles like "Based on the sources..." or conclusions like "In summary..."
5. Keep ONLY directly relevant information

Return ONLY the improved response (no commentary):"""


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
        temperature=0.3,  # Lower temperature for more consistent, factual improvements
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
