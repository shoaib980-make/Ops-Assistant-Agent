"""
Comprehensive Test Suite for Days 1 to 4
Can be executed with standard python unittest (no extra libraries required).
Run with:
    python tests/test_days.py
"""

import unittest
import json
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from langchain_core.messages import HumanMessage
from langgraph.types import Command

# Day 1 imports
from main import extract_information, ExtractedInfo

# Day 2 imports
from rag_chain import build_ops_retriever, format_docs

# Day 3 imports
from tools import ops_handbook_lookup, database_lookup, calculate, draft_email

# Day 4 imports
from ops_graph import build_ops_graph


class TestDay1Extraction(unittest.TestCase):
    """Verifies Day 1 LCEL extraction into Pydantic models."""

    def test_extract_information(self):
        sample = "OpsDesk is an incident ticketing system built using FastAPI and PostgreSQL."
        result = extract_information(sample)
        self.assertIsInstance(result, ExtractedInfo)
        self.assertTrue(len(result.title) > 0)
        self.assertTrue(len(result.summary) > 0)
        self.assertTrue(len(result.keywords) >= 3)


class TestDay2Retrieval(unittest.TestCase):
    """Verifies Day 2 Document Ingestion and Vector Retriever."""

    def test_ops_retriever(self):
        retriever = build_ops_retriever()
        docs = retriever.invoke("What is the refund limit for Tier 1?")
        self.assertTrue(len(docs) > 0)
        formatted = format_docs(docs)
        self.assertIn("SOP-001", formatted)


class TestDay3Tools(unittest.TestCase):
    """Verifies Day 3 Tools execution and schemas."""

    def test_calculate_tool(self):
        result = calculate.invoke({"expression": "12500 * 0.15"})
        self.assertEqual(float(result), 1875.0)

    def test_database_lookup_client(self):
        raw = database_lookup.invoke({"table": "clients", "identifier": "Acme"})
        data = json.loads(raw)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "CL-101")
        self.assertEqual(data[0]["monthly_spend"], 12500)

    def test_database_lookup_tasks(self):
        raw = database_lookup.invoke({"table": "tasks", "identifier": "blocked"})
        data = json.loads(raw)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "TK-502")
        self.assertEqual(data[0]["status"], "Blocked")

    def test_draft_email_tool(self):
        raw = draft_email.invoke({
            "recipient": "test@company.com",
            "subject": "Test Notice",
            "body": "Hello world"
        })
        data = json.loads(raw)
        self.assertEqual(data["status"], "STAGED_FOR_APPROVAL")
        self.assertEqual(data["recipient"], "test@company.com")


class TestDay4LangGraph(unittest.TestCase):
    """Verifies Day 4 LangGraph compilation, routing, and Human-in-the-Loop checkpoint."""

    def test_graph_compilation_and_execution(self):
        graph = build_ops_graph()
        config = {"configurable": {"thread_id": "test-unit-thread-1"}}

        # Test safe route (no email drafting)
        res = graph.invoke({
            "messages": [HumanMessage(content="What is 500 * 2?")],
            "step_count": 0,
            "pending_email": None,
            "email_status": None,
        }, config=config)

        last_msg = res["messages"][-1]
        self.assertIn("1000", str(last_msg.content).replace(",", ""))

    def test_graph_human_approval_interrupt(self):
        graph = build_ops_graph()
        config = {"configurable": {"thread_id": "test-unit-thread-2"}}

        # Query that triggers an email draft
        res = graph.invoke({
            "messages": [HumanMessage(content="Draft an email to admin@test.com about server maintenance.")],
            "step_count": 0,
            "pending_email": None,
            "email_status": None,
        }, config=config)

        # Check that it paused at the interrupt checkpoint
        self.assertIn("__interrupt__", res)
        interrupt_val = res["__interrupt__"][0].value
        self.assertEqual(interrupt_val["type"], "HUMAN_APPROVAL_REQUIRED")

        # Resume with human approval
        resumed = graph.invoke(Command(resume={"approved": True}), config=config)
        final_msg = resumed["messages"][-1]
        self.assertTrue(len(final_msg.content) > 0)


if __name__ == "__main__":
    unittest.main()
