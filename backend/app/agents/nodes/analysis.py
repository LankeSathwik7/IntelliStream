"""Analysis Agent - Extracts insights from retrieved context."""

import time
from typing import Dict

from app.agents.state import AgentState
from app.services.llm import llm_service

ANALYSIS_PROMPT = """Analyze the following context and extract key information.

Context:
{context}

User Query: {query}

Extract:
1. Key entities (people, companies, products, etc.)
2. Overall sentiment (positive, negative, neutral, mixed)
3. 3-5 key facts relevant to the query

Respond in JSON format:
{{
  "entities": [
    {{"name": "...", "type": "person|company|product|location|other"}}
  ],
  "sentiment": {{
    "overall": "positive|negative|neutral|mixed",
    "confidence": 0.0-1.0
  }},
  "key_facts": [
    "fact 1",
    "fact 2"
  ]
}}"""


async def analysis_agent(state: AgentState) -> Dict:
    """
    Analysis Agent: Extracts entities, sentiment, and key facts.

    Updates:
        - entities
        - sentiment
        - key_facts
        - agent_trace
    """
    start_time = time.time()

    context = state.get("context", "")
    query = state["query"]

    if not context:
        return {
            "entities": [],
            "sentiment": {"overall": "neutral", "confidence": 0.5},
            "key_facts": [],
            "agent_trace": state["agent_trace"]
            + [
                {
                    "agent": "analysis",
                    "action": "skipped",
                    "reason": "no_context",
                    "latency_ms": 0,
                }
            ],
        }

    # Get structured analysis from LLM
    prompt = ANALYSIS_PROMPT.format(context=context[:3000], query=query)

    try:
        analysis = await llm_service.generate_json(
            messages=[{"role": "user", "content": prompt}],
            schema_description="entities, sentiment, key_facts",
        )

        entities = analysis.get("entities", [])
        sentiment = analysis.get("sentiment", {"overall": "neutral", "confidence": 0.5})
        key_facts = analysis.get("key_facts", [])

    except Exception:
        entities = []
        sentiment = {"overall": "neutral", "confidence": 0.5}
        key_facts = []

    latency_ms = int((time.time() - start_time) * 1000)

    return {
        "entities": entities,
        "sentiment": sentiment,
        "key_facts": key_facts,
        "agent_trace": state["agent_trace"]
        + [
            {
                "agent": "analysis",
                "action": "analyzed",
                "entities_found": len(entities),
                "sentiment": sentiment.get("overall"),
                "latency_ms": latency_ms,
            }
        ],
    }
