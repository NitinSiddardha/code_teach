"""
app/retrieval/vector_store.py
──────────────────────────────
LANGCHAIN CONCEPT: Vector Stores
──────────────────────────────────
A vector store is a database that stores embeddings and lets you search by similarity.
You ask "what text is most similar to this query?" and it returns the closest matches.

We use Chroma because:
  - It persists to disk (data survives app restarts)
  - Easy to set up locally
  - No external server needed
  - LangChain has great Chroma integration

code.teach uses THREE separate vector stores, each with a different job:
─────────────────────────────────────────────────────────────────────
  1. lesson_store  — student's uploaded notes/material
                     Used to ground tasks in their actual curriculum
                     Query: "what does their material say about inheritance?"

  2. task_store    — every task given + outcome (correct/stuck/almost)
                     Used to avoid repeating tasks, find patterns
                     Query: "what similar tasks has this student done before?"

  3. concept_store — curated concept explanations (you pre-populate this)
                     Used to fetch clean explanations without hallucinating
                     Query: "explain method overriding concisely"
─────────────────────────────────────────────────────────────────────

Start with FAISS during development (in-memory, no setup):
  from langchain_community.vectorstores import FAISS
Switch to Chroma when you want persistence.

Docs to read:
  https://python.langchain.com/docs/concepts/vectorstores
  https://python.langchain.com/docs/integrations/vectorstores/chroma
"""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from config import VECTOR_DIR
from app.models.embeddings import get_embeddings
import os


# ── lesson_store ──────────────────────────────────────────────────────────────

def create_lesson_store(documents: list):
    """
    Build the lesson vector store from the student's uploaded material.
    """
    persist_dir = os.path.join(VECTOR_DIR, "lesson")
    store = Chroma.from_documents(
        documents=documents,
        embedding=get_embeddings(),
        persist_directory=persist_dir
    )
    return store


def load_lesson_store():
    """
    Load an existing lesson store from disk.
    """
    persist_dir = os.path.join(VECTOR_DIR, "lesson")
    if not os.path.exists(persist_dir):
        return None
    return Chroma(persist_directory=persist_dir, embedding_function=get_embeddings())


# ── task_store ────────────────────────────────────────────────────────────────

def get_task_store():
    """
    Returns the task history store (persistent across sessions).
    """
    persist_dir = os.path.join(VECTOR_DIR, "tasks")
    return Chroma(persist_directory=persist_dir, embedding_function=get_embeddings())


def add_task_to_store(task: str, concept: str, outcome: str):
    """
    Add a completed task to the task store.
    """
    doc = Document(
        page_content=task,
        metadata={"concept": concept, "outcome": outcome, "timestamp": os.path.getmtime(VECTOR_DIR)} # simplified timestamp
    )
    store = get_task_store()
    store.add_documents([doc])


# ── concept_store ─────────────────────────────────────────────────────────────

def get_concept_store():
    """
    Returns the curated concept explanation store.
    """
    persist_dir = os.path.join(VECTOR_DIR, "concepts")
    return Chroma(persist_directory=persist_dir, embedding_function=get_embeddings())


def populate_concept_store():
    """
    Pre-populate the concept store with clean explanations.
    """
    concepts = [
        {"concept": "variables", "explanation": "Variables are containers for storing data values. In Python, you don't need to declare types; in Java, you do (int, String, etc.).", "language": "both"},
        {"concept": "loops", "explanation": "Loops (for, while) are used to repeat a block of code multiple times.", "language": "both"},
        {"concept": "inheritance", "explanation": "Inheritance allows a class to inherit attributes and methods from another class. In Java, use 'extends'.", "language": "java"},
        {"concept": "functions", "explanation": "Functions/Methods are blocks of code that only run when called. They can take parameters and return data.", "language": "both"},
    ]
    
    docs = [
        Document(page_content=c["explanation"], metadata={"concept": c["concept"], "language": c["language"]})
        for c in concepts
    ]
    
    store = get_concept_store()
    store.add_documents(docs)

