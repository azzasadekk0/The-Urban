import json
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from backend.config import settings
from backend.agents.state import AgentState
from backend.tools.calculator import (
    detect_calculation_type,
    run_calculation,
    extract_numbers,
    FORMULAS,
)

PARAM_EXTRACT_SYSTEM = """You are a parameter extractor for Egyptian building code calculations.
Given the user query and retrieved legal text, extract numeric parameters needed for the calculation.
Return ONLY valid JSON. Keys must exactly match the required inputs listed.
If a value cannot be found, use null.
"""


def _extract_params_via_llm(
    query: str, chunks: list[dict], calc_type: str, llm: ChatOpenAI
) -> dict:
    """Ask GPT-4o to extract numeric parameters from the query and retrieved context."""
    formula_def = FORMULAS.get(calc_type, {})
    required = formula_def.get("inputs", [])
    context = "\n".join(c["text"] for c in chunks[:4])

    prompt = (
        f"Calculation needed: {calc_type}\n"
        f"Required parameters: {required}\n\n"
        f"User query:\n{query}\n\n"
        f"Retrieved legal context:\n{context}\n\n"
        f"Return JSON with keys: {required}"
    )

    messages = [SystemMessage(content=PARAM_EXTRACT_SYSTEM), HumanMessage(content=prompt)]
    response = llm.invoke(messages)
    raw = response.content.strip().strip("```json").strip("```").strip()
    try:
        return json.loads(raw)
    except Exception:
        return {}


def calculate_node(state: AgentState) -> AgentState:
    """Node 3 — extract numeric params and run the appropriate formula."""
    query = state["query"]
    chunks = state.get("retrieved_chunks", [])

    calc_type = detect_calculation_type(query)
    if not calc_type:
        thought = "### 🧮 Calculation\nNo matching formula detected. Skipping."
        return {**state, "calculation_result": None, "agent_thoughts": [thought]}

    llm = ChatOpenAI(
        model=settings.OPENAI_LLM_MODEL,
        temperature=0,
        openai_api_key=settings.OPENAI_API_KEY,
    )

    params = _extract_params_via_llm(query, chunks, calc_type, llm)
    # Convert string numerics to float
    cleaned = {}
    for k, v in params.items():
        try:
            cleaned[k] = float(v) if v is not None else None
        except (TypeError, ValueError):
            cleaned[k] = None

    result = run_calculation(calc_type, cleaned)

    if "error" in result:
        thought = (
            "### 🧮 Calculation\n"
            f"- **Type:** `{calc_type}`\n"
            f"- **Status:** ❌ Error — {result['error']}\n"
            f"- **Extracted params:** `{cleaned}`"
        )
    else:
        thought = (
            "### 🧮 Calculation\n"
            f"- **Type:** `{calc_type}`\n"
            f"- **Formula:** `{result['formula']}`\n"
            f"- **Inputs:** `{result['inputs']}`\n"
            f"- **Result:** `{result['result']} {result['unit']}`\n"
            f"- **Law Reference:** {result['law_reference']}"
        )

    return {**state, "calculation_result": result, "agent_thoughts": [thought]}
