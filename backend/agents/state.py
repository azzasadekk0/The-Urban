from typing import Optional, Annotated
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict):
    # Input 
    query: str
    session_id: str
    conversation_history: list[dict]  

    # Analyze Node Output 
    language: str          
    context_type: str      
    requires_calculation: bool
    detected_topics: list[str]

    # Retrieve Node Output 
    retrieved_chunks: list[dict]
    active_laws: list[str]
    suppressed_laws: list[str]
    suppression_reasons: list[str]

    # Calculate Node Output 
    calculation_result: Optional[dict]

    # Finalize Node Output 
    compliance_notes: list[str]
    final_response: str

    # Reasoning Trace (for Agent Thoughts UI)
    # Annotated with operator.add so each node appends, not overwrites
    agent_thoughts: Annotated[list[str], operator.add]
