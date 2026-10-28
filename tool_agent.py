"""
Tool-Calling Agent Execution Loop & Tracing
--------------------------------------------
Features:
1. Binding tools to an LLM (`model.bind_tools(OPS_TOOLS)`)
2. Inspecting model-generated `tool_calls`
3. Tool execution and returning `ToolMessage`
4. Multi-step reasoning where the model calls multiple tools in sequence
5. Tool description quality and debugging logs
"""

import json
from dotenv import load_dotenv

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from rag_chain import get_llm
from tools import OPS_TOOLS, TOOLS_BY_NAME

load_dotenv()


def run_tool_calling_loop(user_query: str, max_iterations: int = 5):
    """
    Executes a complete tool-calling loop:
    1. Sends user message + system guidelines to the model
    2. If the model emits tool_calls, runs each tool and appends ToolMessages
    3. Feeds tool outputs back to the model until it produces a final response
    """
    print("=" * 70)
    print(f"USER QUERY: {user_query}")
    print("=" * 70)

    llm = get_llm()
    # Bind tools to the model
    model_with_tools = llm.bind_tools(OPS_TOOLS)

    system_prompt = (
        "You are an Operations Assistant. You have access to four tools:\n"
        "1. ops_handbook_lookup: search company policies and SOPs.\n"
        "2. database_lookup: look up client details or operational tasks.\n"
        "3. calculate: perform exact mathematical calculations.\n"
        "4. draft_email: draft an email for approval.\n\n"
        "Always use the appropriate tool rather than guessing. "
        "If a multi-step task requires information from multiple tools, execute them step-by-step."
    )

    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_query),
    ]

    iteration = 0
    while iteration < max_iterations:
        iteration += 1
        print(f"\n--- [Iteration {iteration}] Calling Model ---")

        response = model_with_tools.invoke(messages)
        messages.append(response)

        # Check if the model requested any tool calls
        if not response.tool_calls:
            print("\n[Model Response Complete - No further tool calls requested]")
            print(f"\nFINAL ASSISTANT ANSWER:\n{response.content}\n")
            return response.content

        print(f"[Model requested {len(response.tool_calls)} tool call(s)]:")
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc["args"]
            tool_call_id = tc["id"]

            print(f"  -> Tool: {tool_name}")
            print(f"     Arguments: {json.dumps(tool_args)}")

            # Execute the tool
            target_tool = TOOLS_BY_NAME.get(tool_name)
            if not target_tool:
                tool_output = f"Error: Tool '{tool_name}' does not exist."
            else:
                try:
                    tool_output = target_tool.invoke(tool_args)
                except Exception as e:
                    tool_output = f"Error running {tool_name}: {str(e)}"

            print(f"     Output Preview: {str(tool_output)[:120]}...")

            # LangChain expects a ToolMessage with the matching tool_call_id
            messages.append(
                ToolMessage(
                    content=str(tool_output),
                    tool_call_id=tool_call_id,
                    name=tool_name
                )
            )

    print("\n[Warning: Reached max iterations without final model response]")
    return None


if __name__ == "__main__":
    # Test 1: Single tool call (Policy lookup)
    run_tool_calling_loop("What is the response SLA for a P1 critical incident?")

    # Test 2: Multi-step reasoning across two different tools (Database lookup + Calculation)
    run_tool_calling_loop(
        "Look up Acme Corp's monthly spend in the database. "
        "If we apply a 15% promotional discount, what will their discounted spend be?"
    )

    # Test 3: Structured drafting tool
    run_tool_calling_loop(
        "Check which task is currently blocked in the database, and draft an email to the assignee "
        "asking for an update."
    )

