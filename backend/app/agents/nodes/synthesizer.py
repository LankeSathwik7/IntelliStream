"""Synthesizer Agent - Combines analysis into coherent insight."""

import time
from typing import Dict

from app.agents.state import AgentState
from app.services.llm import llm_service

SYNTHESIS_PROMPT = """You are a concise, accurate analyst. Answer based ONLY on the provided context.

User Query: {query}

Retrieved Context:
{context}

Key Facts: {key_facts}

RULES:
1. BE CONCISE - Match response length to query complexity. Simple questions get 1-2 sentence answers.
2. ONLY cite [1], [2] etc. if the specific information comes DIRECTLY from that numbered source.
3. If a fact is NOT in any source, do NOT include it - say you don't have that information.
4. Do NOT invent, assume, or hallucinate any information.
5. If sources contradict, note the discrepancy.

Response:"""


async def synthesizer_agent(state: AgentState) -> Dict:
    """
    Synthesizer Agent: Creates a synthesized response from analysis.

    Updates:
        - synthesized_response
        - agent_trace
    """
    start_time = time.time()

    key_facts = state.get("key_facts", [])
    facts_str = "\n".join([f"- {fact}" for fact in key_facts]) if key_facts else "None"

    # Estimate appropriate response length based on query complexity
    query = state["query"]
    query_words = len(query.split())
    # Simple queries (< 10 words) get shorter responses
    max_tokens = 300 if query_words < 10 else 600 if query_words < 25 else 1000

    prompt = SYNTHESIS_PROMPT.format(
        query=query,
        context=state.get("context", "No context available"),
        key_facts=facts_str,
    )

    synthesized_text = await llm_service.generate(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # Very low temperature for factual, grounded responses
        max_tokens=max_tokens,
    )

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "synthesized_response": synthesized_text,
        "agent_trace": state["agent_trace"]
        + [
            {
                "agent": "synthesizer",
                "action": "synthesized",
                "output_length": len(synthesized_text),
                "latency_ms": latency_ms,
            }
        ],
    }
