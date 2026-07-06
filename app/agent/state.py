"""
app/agent/state.py
───────────────────
LANGCHAIN CONCEPT: LangGraph State
────────────────────────────────────
LangGraph is built around a STATE object that flows through all nodes.
Every node reads from state and writes back to state.
The state is the memory of the entire agent loop.

Think of it like a shared Python dict that every function in your agent can see.
After every node runs, the state gets updated and passed to the next node.

This is different from LangChain's basic memory — LangGraph state is:
  - Typed (TypedDict or Pydantic)
  - Persistent across the whole loop
  - Reducible (you can define HOW fields get updated, not just what)

For code.teach, the state holds EVERYTHING about the current session:
  - The lesson plan (generated once, stays fixed)
  - Which module and task we're on
  - The student's live profile (updates after every task)
  - The full conversation history
  - What signal the student sent (if any)
  - The last retrieved context from their notes

Docs to read:
  https://langchain-ai.github.io/langgraph/concepts/low_level/#state
  https://langchain-ai.github.io/langgraph/how-tos/state-reducers/
"""

from typing import TypedDict, Optional, List, Annotated
import operator

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from app.prompts.parsers import LessonPlan, StudentProfile, TeacherResponse


class TeachState(TypedDict):
    """
    The complete state of one teaching session.
    """
    topic:         str
    level:         str
    lesson_plan:   Optional[LessonPlan]

    current_module_idx: int
    current_task_idx:   int
    task_count:         int

    profile: Optional[StudentProfile]
    topic_language: Optional[str]
    topic_concept: Optional[str]

    # Use add_messages reducer so history accumulates
    conversation_history: Annotated[List[BaseMessage], add_messages]

    student_code:     Optional[str]
    student_signal:   Optional[str]
    signal_detail:    Optional[str]
    last_response:    Optional[TeacherResponse]

    retrieved_material: Optional[str]
    retrieved_tasks:    Optional[List[str]]

    should_end_session:  bool
    prereq_gap_detected: Optional[str]
    level_suggestion:    Optional[str]


def initial_state(topic: str, level: str, profile: StudentProfile | None = None) -> TeachState:
    """
    Returns the starting state for a new session.
    """
    return TeachState(
        topic=topic,
        level=level,
        lesson_plan=None,
        current_module_idx=0,
        current_task_idx=0,
        task_count=0,
        profile=profile or StudentProfile(declared_level=level, inferred_level=level),
        topic_language=None,
        topic_concept=None,
        conversation_history=[],
        student_code=None,
        student_signal=None,
        signal_detail=None,
        last_response=None,
        retrieved_material=None,
        retrieved_tasks=None,
        should_end_session=False,
        prereq_gap_detected=None,
        level_suggestion=None,
    )

