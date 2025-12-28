"""Synthesizer Agent - Combines analysis into coherent insight."""

import time
from typing import Dict

from app.agents.state import AgentState
from app.services.llm import llm_service

SYNTHESIS_PROMPT = """You are an expert analyst synthesizing information for a user.

User Query: {query}

Retrieved Context:
{context}

Analysis Results:
- Key Entities: {entities}
- Sentiment: {sentiment}
- Key Facts: {key_facts}

Synthesize this information into a clear, comprehensive response that:
1. Directly addresses the user's query
2. Incorporates relevant facts from the context
3. Mentions key entities when relevant
4. Reflects the overall sentiment if appropriate
5. Uses citations like [1], [2] to reference sources

Provide a well-structured response:"""


async def synthesizer_agent(state: AgentState) -> Dict:
    """
    Synthesizer Agent: Creates a synthesized response from analysis.

    Updates:
        - synthesized_response
        - agent_trace
    """
    start_time = time.time()

    # Format entities and facts for prompt
    entities_str = (
        ", ".join(
            [
                f"{e.get('name', '')} ({e.get('type', '')})"
                for e in state.get("entities", [])
            ]
        )
        or "None identified"
    )

    sentiment = state.get("sentiment", {})
    sentiment_str = f"{sentiment.get('overall', 'neutral')} (confidence: {sentiment.get('confidence', 0.5):.2f})"

    key_facts = state.get("key_facts", [])
    facts_str = "\n".join([f"- {fact}" for fact in key_facts]) or "None extracted"

    prompt = SYNTHESIS_PROMPT.format(
        query=state["query"],
        context=state.get("context", "No context available"),
        entities=entities_str,
        sentiment=sentiment_str,
        key_facts=facts_str,
    )

    synthesized_text = await llm_service.generate(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500,
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
