"""
Ops Assistant Agent - Primary Application Launcher
--------------------------------------------------
By default, running:
    python main.py
automatically launches the modern Web Frontend server and opens your browser!

If you prefer terminal-only mode, pass --cli:
    python main.py --cli
"""

import sys
import uuid
import threading
import webbrowser
import time

from langchain_core.messages import HumanMessage
from langgraph.types import Command
from ops_graph import build_ops_graph
from guardrails import validate_user_input


def run_cli():
    """Terminal-only mode."""
    print("=" * 72)
    print("           OPS ASSISTANT AGENT - TERMINAL CLI")
    print("=" * 72)
    print("Type 'exit' or 'quit' to end the session.\n")

    graph = build_ops_graph()
    thread_id = f"session-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    while True:
        try:
            user_input = input("\n👤 User > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting session. Goodbye!")
            sys.exit(0)

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Session terminated. Goodbye!")
            break

        is_safe, check_result = validate_user_input(user_input)
        if not is_safe:
            print(f"\n🛡️ [Security Guardrail]: {check_result}")
            continue

        print("🤖 [Agent Working...]")
        graph_input = {
            "messages": [HumanMessage(content=user_input)],
            "step_count": 0,
            "pending_email": None,
            "email_status": None,
        }

        result = graph.invoke(graph_input, config=config)
        state = graph.get_state(config)

        if state.next and "human_approval" in state.next:
            interrupts = result.get("__interrupt__", [])
            if interrupts:
                details = interrupts[0].value
                print("\n" + "!" * 72)
                print("⚠️  HUMAN-IN-THE-LOOP APPROVAL REQUIRED")
                print("!" * 72)
                print(f"Recipient: {details.get('recipient')}")
                print(f"Subject:   {details.get('subject')}")
                print(f"Body:\n{details.get('body')}")
                print("-" * 72)

                decision = input("Approve email dispatch? [y/n]: ").strip().lower()
                review_data = {
                    "approved": decision in ("y", "yes", "approve"),
                    "feedback": "Approved by operator." if decision in ("y", "yes") else "Rejected by operator."
                }
                result = graph.invoke(Command(resume=review_data), config=config)

        final_message = result["messages"][-1]
        print(f"\n🤖 Assistant:\n{final_message.content}")


def open_browser():
    """Waits 1.5 seconds for the server to bind, then opens the browser."""
    time.sleep(1.5)
    url = "http://127.0.0.1:8000"
    print(f"\n🌐 Opening Ops Assistant Agent Web Frontend in your browser: {url} ...\n")
    webbrowser.open(url)


def run_web():
    """Starts FastAPI web dashboard and automatically launches web browser."""
    import uvicorn
    from server import app

    print("=" * 72)
    print("       OPS ASSISTANT AGENT - WEB DASHBOARD SERVER")
    print("=" * 72)
    print("Starting Web Server at http://127.0.0.1:8000 ...")
    print("Press CTRL+C to stop the server at any time.\n")

    # Launch browser automatically in background thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Start FastAPI server
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    if "--cli" in sys.argv:
        run_cli()
    else:
        run_web()
