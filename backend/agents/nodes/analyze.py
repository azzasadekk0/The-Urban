import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings
from backend.agents.state import AgentState
from backend.tools.calculator import detect_calculation_type

SYSTEM_PROMPT = """You are a legal query analyzer specializing in Egyptian Building Codes.
Analyze the query and return ONLY valid JSON — no extra text, no markdown.

JSON schema:
{
  "language": "ar" | "en" | "mixed",
  "context_type": "new_city" | "old_city" | "general",
  "requires_calculation": true | false,
  "detected_topics": ["height","setback","parking","fire","area","violation"],
  "reasoning": "one-line explanation"
}

Definitions:
- new_city: New Urban Communities Authority (NUCA) cities (6 Oct, New Cairo, etc.)
- old_city: Traditional municipalities and governorates
- general: Cannot determine from context
"""


def analyze_node(state: AgentState) -> AgentState:
    """Node 1 — classify query intent, language, context, and computation needs."""
    llm = ChatOpenAI(
        model=settings.OPENAI_LLM_MODEL,
        temperature=0,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    messages = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=state["query"]),
    ]
    response = llm.invoke(messages)

    # Parse JSON — strip markdown fences if model added them
    raw = response.content.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]

    try:
        analysis = json.loads(raw.strip())
    except Exception:
        analysis = {
            "language": "mixed",
            "context_type": "general",
            "requires_calculation": False,
            "detected_topics": [],
            "reasoning": "Parse failed — using safe defaults.",
        }

    # Keyword fallback for calculation detection
    if not analysis.get("requires_calculation"):
        if detect_calculation_type(state["query"]):
            analysis["requires_calculation"] = True

    thought = (
        "### 🔍 Query Analysis\n"
        f"- **Language:** `{analysis.get('language')}`\n"
        f"- **Context:** `{analysis.get('context_type')}`\n"
        f"- **Requires Calculation:** `{analysis.get('requires_calculation')}`\n"
        f"- **Topics Detected:** `{', '.join(analysis.get('detected_topics', [])) or 'none'}`\n"
        f"- **Reasoning:** {analysis.get('reasoning')}"
    )

    return {
        **state,
        "language": analysis.get("language", "mixed"),
        "context_type": analysis.get("context_type", "general"),
        "requires_calculation": analysis.get("requires_calculation", False),
        "detected_topics": analysis.get("detected_topics", []),
        "agent_thoughts": [thought],
    }
