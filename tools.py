"""
Operational Tools for Ops Assistant Agent
-----------------------------------------
Defines four production-grade LangChain tools:
1. ops_handbook_lookup: RAG search over company policies & SOPs.
2. database_lookup: Structured query over clients and operational tasks.
3. calculate: Safe mathematical evaluator for billing, refunds, and SLAs.
4. draft_email: Stages a structured email draft for customer or internal communication.
"""

import json
import re
from pathlib import Path
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from rag_chain import build_ops_retriever, format_docs
from supabase_client import query_records, is_supabase_enabled

# Cache the retriever instance so it doesn't re-embed on every call
_RETRIEVER = None


def _get_retriever():
    global _RETRIEVER
    if _RETRIEVER is None:
        _RETRIEVER = build_ops_retriever()
    return _RETRIEVER


# -------------------------------------------------------------
# Tool 1: Operations Handbook Lookup (RAG)
# -------------------------------------------------------------
class HandbookQueryInput(BaseModel):
    query: str = Field(
        description="The operational topic, rule, or SOP question to look up (e.g. 'refund approval limits', 'P1 incident SLA')."
    )


@tool("ops_handbook_lookup", args_schema=HandbookQueryInput)
def ops_handbook_lookup(query: str) -> str:
    """Search company Standard Operating Procedures (SOPs) and policy documentation.
    Use this tool whenever the user asks about company operational rules, approval limits,
    incident escalation procedures, deployment windows, or security guidelines."""
    retriever = _get_retriever()
    docs = retriever.invoke(query)
    if not docs:
        return "No matching operations documentation found."
    return format_docs(docs)


# -------------------------------------------------------------
# Tool 2: Structured Database Lookup (Clients & Tasks)
# -------------------------------------------------------------
class DatabaseQueryInput(BaseModel):
    table: str = Field(
        description="Table to query: must be either 'clients' or 'tasks'."
    )
    identifier: str = Field(
        default="",
        description="Optional filter by ID (e.g., 'CL-101', 'TK-502') or keyword in name/title."
    )


@tool("database_lookup", args_schema=DatabaseQueryInput)
def database_lookup(table: str, identifier: str = "") -> str:
    """Look up structured operational records in the company database (clients or tasks).
    Supports live Supabase querying with automatic fallback to local records.
    Use this tool to find client details (tier, spend, account manager) or task status (priority, assignee).
    Do NOT use this tool for general policy questions (use ops_handbook_lookup instead)."""
    table_key = table.strip().lower()
    if table_key not in ("clients", "tasks"):
        return f"Invalid table '{table}'. Valid tables are: 'clients', 'tasks'."

    filtered = query_records(table_key, identifier)
    if not filtered:
        return f"No records found in '{table}' matching '{identifier}'."
    return json.dumps(filtered, indent=2)


# -------------------------------------------------------------
# Tool 3: Safe Calculator
# -------------------------------------------------------------
class CalculatorInput(BaseModel):
    expression: str = Field(
        description="Mathematical expression to evaluate (e.g. '12500 * 0.15', '350 + 400', '24000 / 12')."
    )


@tool("calculate", args_schema=CalculatorInput)
def calculate(expression: str) -> str:
    """Safely evaluates basic mathematical calculations (addition, subtraction, multiplication, division, percentages).
    Always use this tool for precise financial, refund, discount, or SLA time calculations instead of mental arithmetic."""
    sanitized = expression.strip().replace(" ", "")
    # Allow only digits, basic operators, decimal points, parentheses
    if not re.match(r"^[0-9+\-*/().%]+$", sanitized):
        return f"Error: Invalid characters in expression '{expression}'. Only basic arithmetic is permitted."

    # Convert percentage (e.g. 15% -> 0.15)
    sanitized = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", sanitized)

    try:
        # Use restricted eval for math safety
        result = eval(sanitized, {"__builtins__": None}, {})
        return str(result)
    except Exception as e:
        return f"Error evaluating expression: {str(e)}"


# -------------------------------------------------------------
# Tool 4: Email Drafting Tool
# -------------------------------------------------------------
class DraftEmailInput(BaseModel):
    recipient: str = Field(
        description="The email address or designated recipient role (e.g., 'ops@acmecorp.com', 'Finance VP')."
    )
    subject: str = Field(
        description="Clear, professional subject line reflecting the operational matter."
    )
    body: str = Field(
        description="The full email body including context, findings, or requested actions."
    )


@tool("draft_email", args_schema=DraftEmailInput)
def draft_email(recipient: str, subject: str, body: str) -> str:
    """Stages a draft email for review.
    Use this tool whenever an email needs to be sent to a client or team member.
    Note: This stages the draft in the system but does NOT immediately send it without human review."""
    staged = {
        "status": "STAGED_FOR_APPROVAL",
        "recipient": recipient,
        "subject": subject,
        "body": body,
    }
    return json.dumps(staged, indent=2)


# Export the list of tools for easy agent binding
OPS_TOOLS = [
    ops_handbook_lookup,
    database_lookup,
    calculate,
    draft_email,
]

TOOLS_BY_NAME = {t.name: t for t in OPS_TOOLS}
