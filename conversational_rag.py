"""
Day 2: Conversational RAG with Memory Strategies
------------------------------------------------
Demonstrates:
1. Multi-turn grounded chat with conversation history
2. History-Aware Query Reformulation (resolving pronouns like "it", "that" using prior turns)
3. Buffer Memory vs. Summary Memory strategies
4. Grounded answer generation using retrieved context and conversation history
"""

import os
from typing import List
from dotenv import load_dotenv

from langchain_core.messages import AIMessage, HumanMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from rag_chain import build_ops_retriever, format_docs, get_llm

load_dotenv()


# -------------------------------------------------------------
# 1. History-Aware Query Reformulation Chain
# -------------------------------------------------------------
def build_history_aware_query_chain(llm):
    """
    Sub-chain that takes the chat history and latest user question,
    and reformulates the question into a standalone query suitable for retrieval.
    """
    rephrase_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Given a chat history and the latest user question which might reference context "
            "in the chat history, formulate a standalone question that can be understood "
            "without the chat history. Do NOT answer the question, just reformulate it "
            "if needed and otherwise return it as is."
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    return rephrase_prompt | llm | StrOutputParser()


# -------------------------------------------------------------
# 2. Conversational RAG Q&A Chain
# -------------------------------------------------------------
def build_conversational_rag_chain():
    """
    Complete Conversational RAG pipeline:
    1. Rephrases question with history
    2. Retrieves relevant SOP chunks
    3. Generates grounded answer
    """
    llm = get_llm()
    retriever = build_ops_retriever()
    query_rephrase_chain = build_history_aware_query_chain(llm)

    qa_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """You are an Operations Assistant answering questions based on company SOPs.
Use strictly the provided context to answer the question.
If the context does not contain the answer, say you do not know based on the operations handbook.

Context:
{context}"""
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
    ])

    # LCEL pipeline:
    # 1. Generate standalone query if history exists, or pass input
    # 2. Retrieve docs using standalone query
    # 3. Format docs and pass to QA prompt
    def route_query_and_retrieve(data):
        if data.get("chat_history"):
            standalone_query = query_rephrase_chain.invoke({
                "chat_history": data["chat_history"],
                "input": data["input"]
            })
            retrieved_docs = retriever.invoke(standalone_query)
        else:
            standalone_query = data["input"]
            retrieved_docs = retriever.invoke(data["input"])

        return {
            "context": format_docs(retrieved_docs),
            "chat_history": data.get("chat_history", []),
            "input": data["input"],
            "standalone_query": standalone_query,
        }

    qa_chain = route_query_and_retrieve | qa_prompt | llm | StrOutputParser()
    return qa_chain, query_rephrase_chain


# -------------------------------------------------------------
# 3. Memory Strategy: Summary vs Buffer
# -------------------------------------------------------------
def summarize_history(chat_history: List[BaseMessage], existing_summary: str, llm) -> str:
    """
    Summary Memory Strategy:
    Condenses older conversation turns into a progressive summary to save context window tokens.
    """
    summary_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "Progressively summarize the lines of conversation provided, adding to the previous summary "
            "and returning a new consolidated summary. Focus on operational details and user questions."
        ),
        (
            "human",
            "Current summary:\n{summary}\n\nNew lines of conversation:\n{new_lines}\n\nConsolidated summary:"
        ),
    ])

    formatted_lines = []
    for msg in chat_history:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        formatted_lines.append(f"{role}: {msg.content}")
    new_lines_str = "\n".join(formatted_lines)

    summary_chain = summary_prompt | llm | StrOutputParser()
    return summary_chain.invoke({
        "summary": existing_summary or "None so far.",
        "new_lines": new_lines_str
    })


# -------------------------------------------------------------
# 4. Interactive Multi-turn Demonstration
# -------------------------------------------------------------
def run_multiturn_demo():
    print("=" * 65)
    print("DAY 2 DEMO: Multi-Turn Grounded Chat with Contextual Reformulation")
    print("=" * 65)

    qa_chain, rephrase_chain = build_conversational_rag_chain()
    chat_history: List[BaseMessage] = []

    # Simulated multi-turn dialogue with coreference ("it", "who needs to approve it")
    dialogue = [
        "What is the policy for processing a $350 refund?",
        "Who needs to approve it?",
        "What if the amount is increased to $750?",
    ]

    for turn_idx, user_query in enumerate(dialogue, start=1):
        print(f"\n[Turn {turn_idx}] User asks:")
        print(f"  > \"{user_query}\"")

        # Check what the query rewriter turns this into
        if chat_history:
            rephrased = rephrase_chain.invoke({
                "chat_history": chat_history,
                "input": user_query
            })
            print(f"  [Query Reformulation for Vector Search]: \"{rephrased}\"")
        else:
            print(f"  [First Turn]: Query used as-is.")

        response = qa_chain.invoke({
            "chat_history": chat_history,
            "input": user_query
        })

        print(f"  Ops Assistant:")
        print(f"  {response.strip()}")

        # Update buffer memory
        chat_history.append(HumanMessage(content=user_query))
        chat_history.append(AIMessage(content=response))

    print("\n" + "=" * 65)
    print("DEMO: Summary Memory Strategy (Token Conservation)")
    print("=" * 65)
    llm = get_llm()
    summary = summarize_history(chat_history, "", llm)
    print(f"Generated Rolling Summary of Conversation:\n{summary.strip()}")


if __name__ == "__main__":
    run_multiturn_demo()

