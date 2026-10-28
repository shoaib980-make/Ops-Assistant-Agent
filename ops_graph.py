"""
Stateful LangGraph Operations Assistant Agent
----------------------------------------------
Implements:
1. AgentState with message reducer and execution tracking.
2. Core agent node with system prompt guardrails and max-step safety limits.
3. Conditional edge routing (safe tools vs sensitive actions vs termination).
4. Safe execution tool node (ops_handbook_lookup, database_lookup, calculate).
5. Human-in-the-loop checkpoint & approval node (interrupt before email dispatch).
6. State persistence across turns using MemorySaver checkpointer.
"""

import json
from typing import Literal
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command

from rag_chain import get_llm
from tools import OPS_TOOLS, TOOLS_BY_NAME
from graph_state import AgentState
from guardrails import sanitize_tool_output, validate_user_input

load_dotenv()

# Guardrail: Maximum graph iterations allowed before stopping
MAX_STEPS = 8

SYSTEM_PROMPT = """You are the Ops Assistant Agent for internal company operations.
Your job is to answer questions, look up operational records, calculate figures, and prepare email drafts.

Available capabilities:
1. ops_handbook_lookup: Search internal company SOPs, limits, SLA timelines, and policies.
2. database_lookup: Query structured client and task database records.
3. calculate: Perform accurate financial, discount, and numerical calculations.
4. draft_email: Stage an email draft for review.

OPERATIONAL GUARDRAILS:
- Always use the tools rather than guessing.
- Security Policy: Customer PII (passwords, raw secret tokens) must NEVER be shared or exported.
- Email Sending: You can draft emails via 'draft_email', but emails are NEVER sent without explicit human review and sign-off.
- If you lack sufficient information, state so clearly instead of inventing facts.
"""


# -------------------------------------------------------------
# Node 1: Agent Node
# -------------------------------------------------------------
def agent_node(state: AgentState):
    """Executes the LLM with bound tools and enforces step-limit guardrail."""
    step = state.get("step_count", 0) + 1

    # Guardrail: Max step limit
    if step > MAX_STEPS:
        return {
            "messages": [
                AIMessage(
                    content="Operation halted: Maximum step limit reached without completion. Please refine your request."
                )
            ],
            "step_count": step,
        }

    llm = get_llm().bind_tools(OPS_TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    response = llm.invoke(messages)

    return {
        "messages": [response],
        "step_count": step,
    }


# -------------------------------------------------------------
# Node 2: Safe Tools Node
# -------------------------------------------------------------
def safe_tools_node(state: AgentState):
    """Executes non-sensitive tools (handbook lookup, database lookup, calculate)."""
    last_message = state["messages"][-1]
    tool_messages = []

    for tc in last_message.tool_calls:
        tool_name = tc["name"]
        if tool_name == "draft_email":
            continue  # Handled separately by human approval node

        tool_args = tc["args"]
        call_id = tc["id"]

        target_tool = TOOLS_BY_NAME.get(tool_name)
        if not target_tool:
            result = f"Error: Tool '{tool_name}' not found."
        else:
            try:
                result = target_tool.invoke(tool_args)
            except Exception as e:
                # Guardrail: Tool-error recovery
                result = f"Tool execution failed with error: {str(e)}. Please adjust parameters."

        tool_messages.append(
            ToolMessage(
                content=sanitize_tool_output(str(result)),
                tool_call_id=call_id,
                name=tool_name
            )
        )

    return {"messages": tool_messages}


# -------------------------------------------------------------
# Node 3: Human Approval Node (Sensitive Action Checkpoint)
# -------------------------------------------------------------
def human_approval_node(state: AgentState):
    """
    Suspends graph execution at this checkpoint.
    Surfaces the drafted email to a human operator for approval or rejection.
    """
    last_message = state["messages"][-1]

    # Find the draft_email tool call
    email_call = next(
        (tc for tc in last_message.tool_calls if tc["name"] == "draft_email"),
        None
    )

    if not email_call:
        return {}

    draft_details = email_call["args"]

    # Pause execution here and wait for human input
    human_decision = interrupt({
        "type": "HUMAN_APPROVAL_REQUIRED",
        "action": "SEND_EMAIL",
        "recipient": draft_details.get("recipient"),
        "subject": draft_details.get("subject"),
        "body": draft_details.get("body"),
        "tool_call_id": email_call["id"],
    })

    # Resumed after human input:
    # human_decision is expected to be a dict: {"approved": True/False, "feedback": "optional notes"}
    is_approved = human_decision.get("approved", False) if isinstance(human_decision, dict) else (str(human_decision).lower() in ("yes", "approve", "true"))

    if is_approved:
        status_text = f"SUCCESS: Email to {draft_details.get('recipient')} was APPROVED and officially sent."
        action_status = "APPROVED"
    else:
        feedback = human_decision.get("feedback", "Rejected by human reviewer.") if isinstance(human_decision, dict) else "Rejected by human reviewer."
        status_text = f"CANCELLED: Email dispatch was REJECTED by human reviewer. Reason: {feedback}"
        action_status = "REJECTED"

    tool_msg = ToolMessage(
        content=status_text,
        tool_call_id=email_call["id"],
        name="draft_email"
    )

    return {
        "messages": [tool_msg],
        "pending_email": draft_details,
        "email_status": action_status,
    }


# -------------------------------------------------------------
# Conditional Edge Router
# -------------------------------------------------------------
def route_agent_decision(state: AgentState) -> Literal["safe_tools", "human_approval", "__end__"]:
    """Routes based on model tool calls."""
    last_message = state["messages"][-1]

    # If no tool calls, finish
    if not hasattr(last_message, "tool_calls") or not last_message.tool_calls:
        return END

    tool_names = [tc["name"] for tc in last_message.tool_calls]

    # If sensitive tool called, route to human approval checkpoint
    if "draft_email" in tool_names:
        return "human_approval"

    # Otherwise route to standard safe tools
    return "safe_tools"


# -------------------------------------------------------------
# Graph Construction & Compilation
# -------------------------------------------------------------
def build_ops_graph():
    """Builds and compiles the Ops Assistant StateGraph with memory checkpointer."""
    builder = StateGraph(AgentState)

    # 1. Add nodes
    builder.add_node("agent", agent_node)
    builder.add_node("safe_tools", safe_tools_node)
    builder.add_node("human_approval", human_approval_node)

    # 2. Add edges
    builder.add_edge(START, "agent")

    # Conditional routing from agent
    builder.add_conditional_edges(
        "agent",
        route_agent_decision,
        {
            "safe_tools": "safe_tools",
            "human_approval": "human_approval",
            END: END,
        }
    )

    # Return edges back to agent for synthesis
    builder.add_edge("safe_tools", "agent")
    builder.add_edge("human_approval", "agent")

    # Checkpointer maintains thread history and handles interrupts
    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)


# -------------------------------------------------------------
# Interactive Runner & Demo
# -------------------------------------------------------------
def run_interactive_demo():
    print("=" * 70)
    print("Ops Assistant Agent: Stateful Execution with Human Approval")
    print("=" * 70)

    graph = build_ops_graph()
    thread_config = {"configurable": {"thread_id": "session-ops-001"}}

    # Scenario: User requests an operational check + email draft
    user_query = (
        "Find the blocked task in our database, calculate a 10% refund on their client's monthly spend, "
        "and draft an email to the client's contact about the refund."
    )
    print(f"\n[User Request]: {user_query}\n")

    initial_input = {
        "messages": [HumanMessage(content=user_query)],
        "step_count": 0,
        "pending_email": None,
        "email_status": None,
    }

    # Step 1: Run graph until completion or interrupt
    print("--- [Agent Executing] ---")
    result = graph.invoke(initial_input, config=thread_config)

    # Inspect current state
    state = graph.get_state(thread_config)

    if state.next and "human_approval" in state.next:
        # We hit the interrupt checkpoint!
        interrupt_info = result["__interrupt__"][0].value
        print("\n" + "!" * 70)
        print(">>> HUMAN-IN-THE-LOOP CHECKPOINT REACHED <<<")
        print(f"Action Type: {interrupt_info['type']} -> {interrupt_info['action']}")
        print(f"Recipient:   {interrupt_info['recipient']}")
        print(f"Subject:     {interrupt_info['subject']}")
        print(f"Body:\n{interrupt_info['body']}")
        print("!" * 70)

        # Simulate Human Reviewer decision (Approve with notes)
        print("\n[Human Reviewer]: Reviewing staged email... Action: APPROVED.")
        human_review = {
            "approved": True,
            "feedback": "Approved by Ops Supervisor for immediate dispatch."
        }

        # Step 2: Resume execution from the checkpoint using Command
        print("\n--- [Resuming Graph Execution with Human Approval] ---")
        final_result = graph.invoke(Command(resume=human_review), config=thread_config)

        # Print final model response
        final_message = final_result["messages"][-1]
        print(f"\n[Final Agent Response]:\n{final_message.content}")


if __name__ == "__main__":
    run_interactive_demo()

