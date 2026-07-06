"""
app/agent/tools.py
───────────────────
LANGCHAIN CONCEPTS: Tools + Function Calling
──────────────────────────────────────────────
Tools are functions the LLM can CHOOSE to call.
Instead of the LLM always generating text, it can decide:
  "I need to run this code" or "I need to look this up"

Function Calling = structured way to define tools so the LLM knows:
  - What the tool does (description)
  - What arguments it takes (type hints + docstring)
  - What it returns

In LangChain, you define tools with the @tool decorator.
LangGraph's ReAct agent automatically decides when to call them.

code.teach tools:
─────────────────────────────────────────────────────────────────────
  search_student_notes  — retrieves relevant chunk from lesson_store
                          Used to ground every task in their actual material

  get_task_history      — fetches past tasks on the current concept
                          Used to avoid repeating tasks

  run_code_snippet      — actually EXECUTES the student's code in a sandbox
                          This is the killer feature — agent sees real output
                          not a guess about whether code is correct

  lookup_concept        — fetches a clean explanation from concept_store
                          Used when the agent needs to explain something
                          without hallucinating

  check_prerequisites   — takes a list of concepts a task assumes,
                          checks against StudentProfile scores,
                          returns any gaps
─────────────────────────────────────────────────────────────────────

Docs to read:
  https://python.langchain.com/docs/concepts/tools
  https://python.langchain.com/docs/how_to/custom_tools
"""

import json
import requests

from langchain_core.tools import tool
from app.retrieval.retrievers import get_material_retriever, get_progress_retriever, get_concept_retriever
from config import CONCEPT_WEAK_THRESHOLD


# ── Tool 1: search_student_notes ──────────────────────────────────────────────

@tool
def search_student_notes(query: str) -> str:
    """
    Search the student's uploaded notes for content relevant to the query.
    Returns the most relevant chunk as a string.
    Use this before generating a task to ground it in the student's actual material.
    """
    try:
        retriever = get_material_retriever()
        docs = retriever.get_relevant_documents(query)
        if not docs:
            return "No material uploaded yet."
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception:
        return "No material uploaded yet."


# ── Tool 2: get_task_history ──────────────────────────────────────────────────

@tool
def get_task_history(concept: str) -> str:
    """
    Get past tasks given on this concept and their outcomes.
    Use this to avoid repeating tasks and to see where the student struggled.
    Returns a formatted string of past tasks with their outcomes.
    """
    try:
        retriever = get_progress_retriever()
        docs = retriever.get_relevant_documents(concept)
        if not docs:
            return "No past tasks found for this concept."
        history = []
        for doc in docs:
            history.append(f"Task: {doc.page_content} | Outcome: {doc.metadata.get('outcome', 'unknown')}")
        return "\n".join(history)
    except Exception:
        return "No past tasks found for this concept."


# ── Tool 3: run_code_snippet ──────────────────────────────────────────────────

@tool
def run_code_snippet(code: str, language: str = "python") -> str:
    """
    Execute the student's code using the hosted Piston API and return the output.
    This avoids running arbitrary student code directly on the server.
    """
    # Accept common languages; extendable
    if language not in {"python", "java", "cpp"}:
        return "Language not supported yet."

    try:
        # Map to piston-supported filenames and versions
        if language == "python":
            payload = {
                "language": "python",
                "version": "3.10.0",
                "files": [{"name": "main.py", "content": code}],
            }
        elif language == "java":
            payload = {
                "language": "java",
                "version": "17.0.9",
                "files": [{"name": "Main.java", "content": code}],
            }
        elif language == "cpp":
            payload = {
                "language": "cpp",
                "version": "17.0.0",
                "files": [{"name": "main.cpp", "content": code}],
            }
        response = requests.post("https://emkc.org/api/v2/piston/execute", json=payload, timeout=15)
        response.raise_for_status()
        data = response.json()
        if data.get("run", {}).get("code") == 0:
            stdout = data.get("run", {}).get("stdout", "")
            stderr = data.get("run", {}).get("stderr", "")
            if stdout:
                return stdout
            if stderr:
                return f"Error:\n{stderr}"
            return "Code ran successfully with no output."
        return f"Error:\n{data.get('run', {}).get('stderr', 'Execution failed')}"
    except Exception as exc:
        return f"Could not run code: {exc}"


# ── Tool 4: lookup_concept ────────────────────────────────────────────────────

@tool
def lookup_concept(concept: str) -> str:
    """
    Fetch a clean explanation of a programming concept from the concept store.
    Use this when you need to explain something to the student without hallucinating.
    Returns a concise explanation string.
    """
    try:
        retriever = get_concept_retriever()
        docs = retriever.get_relevant_documents(concept)
        if not docs:
            return "Concept not found in store."
        return docs[0].page_content
    except Exception:
        return f"Concept explanation for {concept} is temporarily unavailable."


# ── Tool 5: check_prerequisites ───────────────────────────────────────────────

@tool
def check_prerequisites(required_concepts: list, student_profile_json: str) -> str:
    """
    Check if the student has mastered the prerequisites for an upcoming task.
    Returns a list of concepts the student hasn't shown enough mastery on.
    
    Args:
        required_concepts: list of concept names the task assumes
        student_profile_json: JSON string of StudentProfile.concept_scores
    """
    try:
        scores = json.loads(student_profile_json)
    except Exception:
        scores = {}
        
    gaps = []
    for concept in required_concepts:
        score = scores.get(concept, 0.0)
        if score < CONCEPT_WEAK_THRESHOLD:
            gaps.append(concept)
            
    if not gaps:
        return "No gaps found."
    return ", ".join(gaps)


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOLS = [
    search_student_notes,
    get_task_history,
    run_code_snippet,
    lookup_concept,
    check_prerequisites,
]

