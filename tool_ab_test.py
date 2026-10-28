"""
Tool Description A/B Testing Framework
--------------------------------------
Evaluates how tool description clarity directly impacts tool-selection accuracy.
Compares:
- Version A (Vague / Poor Descriptions)
- Version B (Precise / Prompt-Engineered Descriptions)
Across 10 evaluation tasks.
"""

from pydantic import BaseModel, Field
from langchain_core.tools import tool
from rag_chain import get_llm


# -------------------------------------------------------------------
# Version A: Vague / Low-Quality Descriptions
# -------------------------------------------------------------------
@tool("handbook_vague")
def handbook_vague(text: str) -> str:
    """Useful to find information."""
    return "handbook result"


@tool("database_vague")
def database_vague(info: str) -> str:
    """Useful to query records."""
    return "database result"


@tool("calc_vague")
def calc_vague(num: str) -> str:
    """Useful for numbers."""
    return "calc result"


@tool("email_vague")
def email_vague(msg: str) -> str:
    """Useful to send or write something."""
    return "email result"


TOOLS_A = [handbook_vague, database_vague, calc_vague, email_vague]


# -------------------------------------------------------------------
# Version B: Clear, Boundary-Aware, Prompt-Engineered Descriptions
# -------------------------------------------------------------------
@tool("ops_handbook_lookup")
def ops_handbook_lookup(query: str) -> str:
    """Search company Standard Operating Procedures (SOPs), refund limits, SLAs, and security rules.
    Use ONLY for company policy, procedure, or guideline questions. Do NOT use for customer records."""
    return "handbook result"


@tool("database_lookup")
def database_lookup(table: str, identifier: str = "") -> str:
    """Look up structured customer records or operational tasks in the company database (e.g. client spend, assigned tasks).
    Do NOT use for general company policies (use ops_handbook_lookup instead)."""
    return "database result"


@tool("calculate")
def calculate(expression: str) -> str:
    """Safely calculates arithmetic expressions (e.g. discounts, SLA remaining, refund calculations).
    Always use this instead of mental math for financial calculations."""
    return "calc result"


@tool("draft_email")
def draft_email(recipient: str, subject: str, body: str) -> str:
    """Stages a draft email for human review before sending.
    Use when user explicitly asks to draft or write an email to an employee or client."""
    return "email result"


TOOLS_B = [ops_handbook_lookup, database_lookup, calculate, draft_email]


# -------------------------------------------------------------------
# 10 Evaluation Tasks with Expected Target Tool
# -------------------------------------------------------------------
EVAL_TASKS = [
    ("What is our maximum refund limit for Tier 1 support?", "handbook"),
    ("Look up the monthly spend for client CL-101.", "database"),
    ("Compute 12500 multiplied by 0.15.", "calc"),
    ("Draft an email to Alex about the database migration delay.", "email"),
    ("What is the response SLA for a P1 infrastructure outage?", "handbook"),
    ("Find which tasks are assigned to Maya.", "database"),
    ("Calculate 350 + 400 + 150.", "calc"),
    ("What are the allowed hours for production server deployments?", "handbook"),
    ("Check the account status and tier of BlueWave Logistics.", "database"),
    ("Write a message to send to it@bluewave.com regarding contract renewal.", "email"),
]


def evaluate_tool_selection():
    llm = get_llm()
    model_a = llm.bind_tools(TOOLS_A)
    model_b = llm.bind_tools(TOOLS_B)

    results = []

    print("Running Tool Description A/B Test across 10 Evaluator Tasks...\n")

    for idx, (query, expected_category) in enumerate(EVAL_TASKS, start=1):
        # Test Version A
        resp_a = model_a.invoke(query)
        selected_a = resp_a.tool_calls[0]["name"] if resp_a.tool_calls else "NO_TOOL"

        # Check correctness for A
        correct_a = expected_category in selected_a.lower()

        # Test Version B
        resp_b = model_b.invoke(query)
        selected_b = resp_b.tool_calls[0]["name"] if resp_b.tool_calls else "NO_TOOL"

        # Check correctness for B
        correct_b = expected_category in selected_b.lower()

        results.append({
            "task_id": idx,
            "query": query,
            "expected": expected_category,
            "selected_a": selected_a,
            "correct_a": correct_a,
            "selected_b": selected_b,
            "correct_b": correct_b,
        })

    # Summary table
    print(f"{'#':<3} | {'Expected':<10} | {'Version A Tool':<18} | {'Ver A':<6} | {'Version B Tool':<22} | {'Ver B':<6}")
    print("-" * 75)
    score_a = sum(1 for r in results if r["correct_a"])
    score_b = sum(1 for r in results if r["correct_b"])

    for r in results:
        status_a = "PASS" if r["correct_a"] else "FAIL"
        status_b = "PASS" if r["correct_b"] else "PASS" if r["correct_b"] else "FAIL"
        print(f"{r['task_id']:<3} | {r['expected']:<10} | {r['selected_a']:<18} | {status_a:<6} | {r['selected_b']:<22} | {status_b:<6}")

    print("-" * 75)
    print(f"Version A (Vague Descriptions) Accuracy: {score_a}/10 ({score_a*10}%)")
    print(f"Version B (Engineered Descriptions) Accuracy: {score_b}/10 ({score_b*10}%)")


if __name__ == "__main__":
    evaluate_tool_selection()

