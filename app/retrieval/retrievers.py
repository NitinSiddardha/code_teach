"""
app/retrieval/retrievers.py
────────────────────────────
LANGCHAIN CONCEPT: Retrievers
───────────────────────────────
A Retriever is a LangChain interface that takes a query and returns Documents.
It's an abstraction over the vector store — you can have custom logic inside.

Standard retriever: store.as_retriever(search_kwargs={"k": 4})
Custom retriever: subclass BaseRetriever, override _get_relevant_documents()

code.teach has two custom retrievers worth building:

  1. ProgressAwareRetriever
     — filters task_store by outcome="wrong"
     — weighted by recency (newer wrong tasks ranked higher)
     — the agent naturally revisits weak spots without explicit programming
     — used by: decide_next_task node in the agent

  2. MaterialRetriever
     — wraps lesson_store
     — filters by relevance to the current concept being taught
     — returns the most relevant chunk from student's own notes
     — used by: give_task node to ground tasks in student's material

Docs to read:
  https://python.langchain.com/docs/concepts/retrievers
  https://python.langchain.com/docs/how_to/custom_retriever
"""

from config import TOP_K_RESULTS
from app.retrieval.vector_store import get_task_store, load_lesson_store, get_concept_store

from typing import List
from langchain_core.retrievers import BaseRetriever
from langchain_core.documents import Document
from langchain_core.callbacks import CallbackManagerForRetrieverRun
from config import TOP_K_RESULTS
from app.retrieval.vector_store import get_task_store, load_lesson_store, get_concept_store


# ── ProgressAwareRetriever ────────────────────────────────────────────────────

class ProgressAwareRetriever(BaseRetriever):
    """
    Retrieves past tasks filtered by outcome.
    """
    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        store = get_task_store()
        # Step 1: similarity search with metadata filter
        docs = store.similarity_search(
            query,
            k=TOP_K_RESULTS,
            filter={"outcome": "wrong"}
        )
        # Step 2: sort by recency (timestamp in metadata)
        docs.sort(key=lambda d: d.metadata.get("timestamp", 0), reverse=True)
        return docs


# ── MaterialRetriever ─────────────────────────────────────────────────────────

class MaterialRetriever(BaseRetriever):
    """
    Retrieves the most relevant chunk from the student's uploaded notes.
    """
    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> List[Document]:
        store = load_lesson_store()
        if not store:
            return []
        return store.similarity_search(query, k=2)


# ── Convenience functions ─────────────────────────────────────────────────────

def get_material_retriever() -> MaterialRetriever:
    """Returns a MaterialRetriever instance."""
    return MaterialRetriever()


def get_progress_retriever() -> ProgressAwareRetriever:
    """Returns a ProgressAwareRetriever instance."""
    return ProgressAwareRetriever()


def get_concept_retriever():
    """Returns a simple retriever over the concept store."""
    store = get_concept_store()
    return store.as_retriever(search_kwargs={"k": 2})

