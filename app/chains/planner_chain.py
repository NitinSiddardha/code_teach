"""
app/chains/planner_chain.py
────────────────────────────
LANGCHAIN CONCEPT: Chains (LCEL — LangChain Expression Language)
──────────────────────────────────────────────────────────────────
A Chain connects components with the pipe operator (|).
Each component's output becomes the next component's input.

LCEL syntax:
    chain = prompt | llm | output_parser

This is called LCEL (LangChain Expression Language).
It's LangChain's modern way to build pipelines.

Why chains vs agents?
  - Chain  = linear, deterministic, no decisions. Runs A → B → C always.
  - Agent  = dynamic, makes decisions, can loop. Runs different paths.

The planner is a CHAIN because:
  - It runs once, linearly
  - No decisions needed — just read material and produce a plan
  - Input → Output, that's it

The teacher loop is an AGENT because:
  - It runs many times
  - Decisions depend on student behaviour
  - Different paths based on signals, code quality, etc.

Docs to read:
  https://python.langchain.com/docs/concepts/lcel
  https://python.langchain.com/docs/concepts/runnables
"""

from app.models.llm import smart_llm
from app.prompts.templates import PLANNER_PROMPT
from app.prompts.parsers import LessonPlan, lesson_plan_parser
from app.retrieval.vector_store import load_lesson_store


def build_planner_chain():
    """
    Builds and returns the lesson planner chain.
    """
    return PLANNER_PROMPT | smart_llm | lesson_plan_parser


def run_planner(topic: str, level: str, previous_session=None) -> LessonPlan:
    """
    Runs the planner chain to generate a lesson plan.
    Called once at the start of each session.
    """
    material = get_material_summary() or "No material uploaded"
    
    chain = build_planner_chain()
    plan = chain.invoke({
        "topic": topic,
        "level": level,
        "material": material,
        "previous_session": str(previous_session) if previous_session else "First session",
        "format_instructions": lesson_plan_parser.get_format_instructions()
    })
    return plan


def get_material_summary() -> str:
    """
    Gets a text summary of the student's uploaded material for the planner.
    """
    try:
        store = load_lesson_store()
        if not store:
            return None
        docs = store.similarity_search("main topics concepts overview", k=5)
        return "\n\n".join([doc.page_content for doc in docs])
    except Exception:
        return None

