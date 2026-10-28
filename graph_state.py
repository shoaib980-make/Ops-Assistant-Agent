"""
Day 4: LangGraph State Definition
---------------------------------
Defines the state structure that flows through the LangGraph agent nodes.
"""

from typing import Annotated, Any, Dict, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    State object passed between all nodes in the Ops Assistant graph:
    - messages: Thread history with add_messages reducer (auto-appends new messages).
    - pending_email: Stores email draft details waiting for human approval.
    - email_status: Status of the sensitive email action ('PENDING', 'APPROVED', 'REJECTED').
    - step_count: Guardrail to enforce maximum iteration limits and prevent infinite loops.
    """
    messages: Annotated[List[BaseMessage], add_messages]
    pending_email: Optional[Dict[str, Any]]
    email_status: Optional[str]
    step_count: int

