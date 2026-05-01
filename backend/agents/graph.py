from langgraph.graph import StateGraph, END
from backend.agents.state import AgentState
from backend.agents.nodes.analyze import analyze_node
from backend.agents.nodes.retrieve import retrieve_node
from backend.agents.nodes.calculate import calculate_node
from backend.agents.nodes.finalize import finalize_node


def _route_after_retrieve(state: AgentState) -> str:
    """Conditional edge: go to calculate if needed, otherwise straight to finalize."""
    if state.get("requires_calculation"):
        return "calculate"
    return "finalize"


def build_graph() -> StateGraph:
    """
    Build the LangGraph StateGraph for The Urban.

    Flow:
      analyze → retrieve → [calculate? → finalize] or [finalize]
                                                          ↓
                                                         END
    """
    graph = StateGraph(AgentState)

    # Register nodes
    graph.add_node("analyze", analyze_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("calculate", calculate_node)
    graph.add_node("finalize", finalize_node)

    # Edges
    graph.set_entry_point("analyze")
    graph.add_edge("analyze", "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        _route_after_retrieve,
        {"calculate": "calculate", "finalize": "finalize"},
    )
    graph.add_edge("calculate", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


# Singleton compiled graph
urban_graph = build_graph()
