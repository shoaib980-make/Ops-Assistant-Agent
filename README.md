# Ops Assistant Agent: Week 4 Project

An orchestrated, production-grade AI Operations Assistant built with **LangChain**, **LangGraph**, **Pydantic**, and **OpenAI**. 

This repository tracks the day-by-day evolution from raw LLM calls and basic LCEL chains into a stateful, multi-tool LangGraph agent with conversation memory, guardrails, and human-in-the-loop approvals.

---

## 📌 Project Overview

The **Ops Assistant Agent** assists an operations team by:
1. **Answering operational SOPs and company policies** using Retrieval-Augmented Generation (RAG) over an internal handbook.
2. **Querying structured company data** (client MRR, account managers, and operational tasks).
3. **Performing safe financial and numerical calculations** (discounts, refunds, SLA calculations) without mental arithmetic hallucinations.
4. **Drafting customer and internal emails** with a mandatory **Human-in-the-Loop** checkpoint before dispatching sensitive actions.
5. **Enforcing strict operational guardrails** against PII leakage, prompt injection, and runaway execution loops.

---

## 📁 Repository Structure

```text
Ops-Assistant-Agent/
├── data/
│   ├── ops_handbook.md         # Internal company SOPs (Refund limits, P1 SLAs, Deployments, Security)
│   └── ops_database.json       # Structured operational database (Clients, Tasks)
├── main.py                     # Day 1: Information Extractor rebuilt in LCEL with Pydantic
├── raw_extractor.py            # Day 1: Baseline raw OpenAI SDK implementation
├── chain_demo.py               # Day 1: Minimal 3-step LCEL string chain demo
├── rag_chain.py                # Day 2: LangChain RAG pipeline (Recursive splitter + InMemoryVectorStore)
├── conversational_rag.py       # Day 2: Multi-turn RAG with query reformulation & memory strategies
├── tools.py                    # Day 3: Four production tools with strict Pydantic schemas
├── tool_agent.py               # Day 3: Dynamic tool-calling agent loop with execution tracing
├── tool_ab_test.py             # Day 3: Hands-on A/B test measuring tool selection accuracy
├── graph_state.py              # Day 4: TypedDict state definition with message reducers
├── ops_graph.py                # Day 4: LangGraph stateful workflow with Human-in-the-Loop checkpoint
├── requirements.txt            # Project dependencies
└── README.md                   # Complete documentation
```

---

## 📅 Daily Progression & Concepts Learned

### Day 1: LangChain Core & LCEL Composition
- **Goal**: Move from raw API calls to declarative LCEL (`prompt | model | parser`).
- **Key Concepts**: `ChatPromptTemplate`, `ChatOpenAI`, `PydanticOutputParser`, structured schemas.
- **Files**: [`main.py`](main.py), [`raw_extractor.py`](raw_extractor.py), [`chain_demo.py`](chain_demo.py).

### Day 2: Retrieval Chains & Conversation Memory
- **Goal**: Connect private operations knowledge and manage multi-turn chat memory.
- **Key Concepts**: `InMemoryVectorStore`, `RecursiveCharacterTextSplitter`, LangChain `Retriever` interface, History-Aware query reformulation (resolving pronouns like *"it"*), Buffer vs Summary memory strategies.
- **Files**: [`rag_chain.py`](rag_chain.py), [`conversational_rag.py`](conversational_rag.py), [`data/ops_handbook.md`](data/ops_handbook.md).

### Day 3: Tools & Tool-Calling Agents
- **Goal**: Give the model dynamic capabilities and verify tool description engineering.
- **Key Concepts**: `@tool` decorator, Pydantic `args_schema`, `model.bind_tools()`, tool message resolution, A/B testing tool descriptions across 10 evaluation tasks.
- **Files**: [`tools.py`](tools.py), [`tool_agent.py`](tool_agent.py), [`tool_ab_test.py`](tool_ab_test.py), [`data/ops_database.json`](data/ops_database.json).

### Day 4: LangGraph Fundamentals & Human-in-the-Loop
- **Goal**: Build a stateful, cyclic workflow with routing and safety checkpoints.
- **Key Concepts**: `StateGraph`, `AgentState`, `START`, `END`, conditional routing edges, `MemorySaver` thread checkpointer, and `interrupt()` / `Command(resume=...)` for human approval before sending emails.
- **Files**: [`graph_state.py`](graph_state.py), [`ops_graph.py`](ops_graph.py).

---

## 🚀 Setup & Execution

### 1. Prerequisites & Virtual Environment
Ensure you have Python 3.10+ installed:
```powershell
# Activate existing virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 2. Environment Configuration
Create or verify your `.env` file in the project root:
```env
OPENAI_API_KEY="your-api-key"
OPENAI_MODEL="gpt-4o-mini"
OPENAI_BASE_URL="optional-proxy-or-base-url"
```

### 3. Running Daily Modules

#### Run Day 1 (LCEL Extractor):
```powershell
python main.py
```

#### Run Day 2 (Conversational RAG with Memory):
```powershell
python conversational_rag.py
```

#### Run Day 3 (Tool-Calling Agent & A/B Test):
```powershell
# Test multi-tool calling agent
python tool_agent.py

# Run 10-task tool selection A/B test
python tool_ab_test.py
```

#### Run Day 4 (LangGraph Stateful Agent with Human Approval):
```powershell
python ops_graph.py
```

---

## 🛡️ Guardrails & Safety Architecture

1. **Deterministic Financial Math**: Mathematical and discount calculations are delegated to the Python evaluator tool (`calculate`), completely eliminating LLM mental math hallucination.
2. **PII and Data Protection**: Guardrails embedded in the system prompt reject queries attempting to export raw secrets or customer credentials.
3. **Execution Limits (`MAX_STEPS = 8`)**: Prevents runaway execution loops or recursion depth errors in multi-tool agent cycles.
4. **Human-in-the-Loop Checkpoint**: Any destructive or outward-facing action (such as sending an email) triggers an `interrupt()`, saving graph state to memory and requiring explicit operator sign-off (`APPROVED` / `REJECTED`) before resuming.

