"""LangGraph workflow definition for IntelliStream."""

from typing import AsyncGenerator, Dict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.agents.nodes import analysis, research, response, router, synthesizer, reflection
from app.agents.state import AgentState, create_initial_state


def build_intellistream_graph():
    """
    Build the 6-agent IntelliStream workflow.

    Graph structure:

    START -> Router -> [condition]
                      |-> research -> Research -> Analysis -> Synthesis -> Reflection -> Response -> END
                      |-> direct -> Response -> END
                      |-> clarify -> Response -> END
    """

    # Create the graph
    workflow = StateGraph(AgentState)

    # Add all nodes
    workflow.add_node("router", router.router_agent)
    workflow.add_node("research", research.research_agent)
    workflow.add_node("analysis", analysis.analysis_agent)
    workflow.add_node("synthesizer", synthesizer.synthesizer_agent)
    workflow.add_node("reflection", reflection.reflection_agent)
    workflow.add_node("response", response.response_agent)

    # Define edges
    workflow.add_edge(START, "router")

    # Conditional routing from router
    workflow.add_conditional_edges(
        "router",
        router.route_decision,
        {"research": "research", "direct": "response", "clarify": "response"},
    )

    # Research path (now includes reflection)
    workflow.add_edge("research", "analysis")
    workflow.add_edge("analysis", "synthesizer")
    workflow.add_edge("synthesizer", "reflection")
    workflow.add_edge("reflection", "response")

    # End
    workflow.add_edge("response", END)

    # Compile with checkpointer for state persistence
    checkpointer = MemorySaver()
    return workflow.compile(checkpointer=checkpointer)


# Singleton graph instance
_graph = None


def get_graph():
    """Get or create the agent graph."""
    global _graph
    if _graph is None:
        _graph = build_intellistream_graph()
    return _graph


async def run_agent_workflow(
    query: str,
    thread_id: str,
    user_id: str = None,
) -> Dict:
    """
    Run the complete agent workflow.

    Args:
        query: User's query
        thread_id: Conversation thread ID
        user_id: Optional user ID

    Returns:
        Final state with response and metadata
    """
    graph = get_graph()

    # Create initial state
    initial_state = create_initial_state(
        query=query,
        thread_id=thread_id,
        user_id=user_id,
    )

    # Run the graph
    config = {"configurable": {"thread_id": thread_id}}
    final_state = await graph.ainvoke(initial_state, config)

    return {
        "response": final_state.get("final_response", ""),
        "thread_id": thread_id,
        "sources": final_state.get("sources", []),
        "agent_trace": final_state.get("agent_trace", []),
        "latency_ms": final_state.get("total_latency_ms", 0),
    }


async def stream_agent_workflow(
    query: str,
    thread_id: str,
    user_id: str = None,
    history: list = None,
) -> AsyncGenerator[Dict, None]:
    """
    Stream the agent workflow with real-time updates.

    Yields:
        SSE-compatible event dictionaries with token-by-token streaming
    """
    from app.services.llm import llm_service

    graph = get_graph()

    initial_state = create_initial_state(
        query=query,
        thread_id=thread_id,
        user_id=user_id,
        history=history,
    )

    config = {"configurable": {"thread_id": thread_id}}

    # Track sources and state from nodes
    sources = []
    final_state = {}
    synthesized_response = ""
    route_decision = "direct"

    # First, run through agents to gather context (excluding final response generation)
    async for event in graph.astream_events(initial_state, config, version="v2"):
        event_type = event.get("event")

        if event_type == "on_chain_start":
            node_name = event.get("name", "")
            if node_name in ["router", "research", "analysis", "synthesizer", "reflection", "response"]:
                yield {
                    "type": "agent_status",
                    "data": {"agent": node_name, "status": "started"},
                }

        elif event_type == "on_chain_end":
            node_name = event.get("name", "")
            output = event.get("data", {}).get("output", {})

            # Capture data from each node
            if node_name == "router":
                route_decision = output.get("route_decision", "direct")

            if node_name == "research" and output.get("sources"):
                sources = output.get("sources", [])

            if node_name == "synthesizer":
                synthesized_response = output.get("synthesized_response", "")

            if node_name == "reflection":
                # Use reflected response if available
                if output.get("synthesized_response"):
                    synthesized_response = output.get("synthesized_response")

            if node_name == "response":
                final_state = output

            if node_name in ["router", "research", "analysis", "synthesizer", "reflection", "response"]:
                yield {
                    "type": "agent_status",
                    "data": {"agent": node_name, "status": "completed"},
                }

    # Now stream the final response token by token
    import asyncio

    final_response = final_state.get("final_response", "")

    if final_response:
        # Stream the response word by word for better UX
        words = final_response.split(" ")
        streamed_content = ""

        for i, word in enumerate(words):
            if i > 0:
                streamed_content += " "
            streamed_content += word

            # Send token update for EVERY word for smooth streaming
            yield {
                "type": "token",
                "data": {"content": streamed_content},
            }
            # Slightly longer delay for visible streaming effect
            await asyncio.sleep(0.035)

        # Send final response with sources
        yield {
            "type": "response",
            "data": {
                "content": final_response,
                "sources": sources,
            },
        }

    # Send completion event
    yield {"type": "done", "data": {"thread_id": thread_id}}
