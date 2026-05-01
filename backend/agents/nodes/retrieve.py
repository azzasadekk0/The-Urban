from backend.agents.state import AgentState
from backend.rag.retriever import hierarchical_retrieve


def retrieve_node(state: AgentState) -> AgentState:
    """Node 2 — hierarchical retrieval with 2024/2021 conflict suppression."""
    result = hierarchical_retrieve(
        query=state["query"],
        context_type=state["context_type"],
    )

    chunks = result["chunks"]
    active_laws = result["active_laws"]
    suppressed_laws = result["suppressed_laws"]
    suppression_reasons = result["suppression_reasons"]

    # Build thought log
    lines = ["### 📚 Hierarchical Retrieval"]
    lines.append(f"- **Chunks retrieved:** `{len(chunks)}`")
    lines.append(
        f"- **Active laws:** {', '.join(f'`{l}`' for l in active_laws) if active_laws else '`none`'}"
    )

    if suppressed_laws:
        lines.append("\n**⚠️ Suppressed Documents (overridden by higher-priority law):**")
        for reason in suppression_reasons:
            lines.append(f"  - {reason}")
    else:
        lines.append("- **Suppression:** None required.")

    lines.append("\n**Top Chunks (priority order):**")
    for i, c in enumerate(chunks[:5], 1):
        m = c.get("metadata", {})
        lines.append(
            f"  {i}. [{m.get('law_name_en', '?')}] "
            f"Priority={c['priority']} | Score={c['score']:.3f} | Page {m.get('page', '?')}"
        )

    return {
        **state,
        "retrieved_chunks": chunks,
        "active_laws": active_laws,
        "suppressed_laws": suppressed_laws,
        "suppression_reasons": suppression_reasons,
        "agent_thoughts": ["\n".join(lines)],
    }
