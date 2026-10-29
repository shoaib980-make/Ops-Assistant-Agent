"""
Operations Knowledge Base Retrieval Pipeline (RAG)
---------------------------------------------------
Capabilities:
1. Document ingestion and text splitting (RecursiveCharacterTextSplitter)
2. Vector embeddings and indexing using InMemoryVectorStore
3. Retriever abstraction in LangChain
4. LCEL composition for RAG:
   { "context": retriever | format_docs, "question": RunnablePassthrough() }
   | prompt
   | model
   | StrOutputParser()
"""

import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

try:
    from langchain_community.vectorstores import FAISS
    HAS_FAISS = True
except ImportError:
    HAS_FAISS = False

load_dotenv()


def get_llm():
    config = {
        "model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        "api_key": os.environ["OPENAI_API_KEY"],
        "temperature": 0,
    }
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        config["base_url"] = base_url
    return ChatOpenAI(**config)


def get_embeddings():
    config = {
        "api_key": os.environ["OPENAI_API_KEY"],
    }
    base_url = os.getenv("OPENAI_BASE_URL")
    if base_url:
        config["base_url"] = base_url
    return OpenAIEmbeddings(**config)


def format_docs(docs: list[Document]) -> str:
    """Format retrieved documents with their source titles."""
    formatted = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "Unknown")
        formatted.append(f"[Source {i} ({source})]:\n{doc.page_content}")
    return "\n\n".join(formatted)


def build_ops_retriever():
    """Load handbook, chunk into sections, and build high-performance vector retriever (FAISS / VectorStore)."""
    handbook_path = Path(__file__).parent / "data" / "ops_handbook.md"
    content = handbook_path.read_text(encoding="utf-8")

    # Split document by markdown headings or chunk size
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=50,
        separators=["\n## ", "\n\n", "\n", " "]
    )
    docs = splitter.create_documents(
        texts=[content],
        metadatas=[{"source": "data/ops_handbook.md"}]
    )

    embeddings = get_embeddings()

    # Use FAISS vector store for high-performance indexing
    if HAS_FAISS:
        vector_store = FAISS.from_documents(docs, embeddings)
    else:
        vector_store = InMemoryVectorStore(embedding=embeddings)
        vector_store.add_documents(docs)

    # Convert to LangChain Retriever (retrieve top 2 relevant chunks)
    return vector_store.as_retriever(search_kwargs={"k": 2})


def build_rag_chain(retriever):
    """Compose the RAG chain using LCEL."""
    template = """You are an Operations Assistant helping employees follow company SOPs.
Use strictly the provided context to answer the question.
If the answer cannot be found in the context, say: "I do not have information on that in the operations handbook."

Context:
{context}

Question:
{question}

Answer with specific details and mention relevant SOP numbers when available:"""

    prompt = ChatPromptTemplate.from_template(template)
    model = get_llm()
    parser = StrOutputParser()

    chain = (
        {
            "context": retriever | format_docs,
            "question": RunnablePassthrough(),
        }
        | prompt
        | model
        | parser
    )
    return chain


if __name__ == "__main__":
    print("--- Initializing Operations RAG Pipeline ---")
    retriever = build_ops_retriever()
    rag_chain = build_rag_chain(retriever)

    test_questions = [
        "What is the refund limit an Operations Lead can approve?",
        "What should I do if there is a P1 critical outage?",
        "Can we deploy to production on a Friday afternoon?",
    ]

    for q in test_questions:
        print(f"\nQ: {q}")
        response = rag_chain.invoke(q)
        print(f"A: {response}")

