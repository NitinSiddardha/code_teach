"""
app/agent/nodes.py
───────────────────
LANGCHAIN CONCEPT: LangGraph Nodes
────────────────────────────────────
In LangGraph, a NODE is just a Python function that:
  - Takes the current state
  - Does some work (calls LLM, retrieves docs, runs tool, updates profile)
  - Returns a PARTIAL state update (only the fields that changed)

LangGraph merges your partial update into the full state automatically.
You never return the whole state — just what changed.

The agent graph in teacher_agent.py connects these nodes with edges.
The ROUTER node decides which node runs next based on state flags.

Nodes in code.teach:
──────────────────────────────────────────────────────────────────────
  plan_lesson         — runs ONCE at start, generates LessonPlan
  retrieve_context    — fetches relevant material before each task
  give_task           — generates the next task using TEACH_PROMPT
  evaluate_code       — evaluates student's submission using FEEDBACK_PROMPT
  handle_signal       — responds to student signals (too_hard, etc.)
  check_prerequisites — detects prereq gaps before giving a task
  update_profile      — updates StudentProfile after every task
  router              — decides what to do next (not an LLM call, pure logic)
  end_session         — generates SessionSummary, saves to disk
──────────────────────────────────────────────────────────────────────

Docs to read:
  https://langchain-ai.github.io/langgraph/concepts/low_level/#nodes
"""

import json
from datetime import datetime
from langchain_core.messages import AIMessage, HumanMessage
from app.agent.state import TeachState
from app.prompts.templates import TEACH_PROMPT, FEEDBACK_PROMPT, PLANNER_PROMPT, SIGNAL_PROMPT, DETOUR_PROMPT
from app.prompts.parsers import (
    TeacherResponse,
    RichFeedback,
    Module,
    LessonPlan,
    SessionSummary,
    teacher_response_parser,
    lesson_plan_parser,
    session_summary_parser,
)
from app.models.llm import get_llm_for_level, smart_llm
from app.agent.tools import (
    search_student_notes, 
    get_task_history, 
    run_code_snippet, 
    lookup_concept, 
    check_prerequisites
)
from app.memory.session_memory import save_session
from app.chains.planner_chain import run_planner
from app.chains.difficulty_chain import get_next_concept, analyse_performance


def build_fallback_plan(topic: str, level: str) -> LessonPlan:
    return LessonPlan(
        topic=topic,
        modules=[
            Module(
                title="Core foundations",
                concepts=["variables", "control flow"],
                task_count=2,
                prerequisites=[],
            )
        ],
        total_tasks=2,
        estimated_hours=0.5,
        notes=f"Fallback lesson plan for {level} learners because the model endpoint was unavailable.",
    )


def build_fallback_response(state: TeachState, *, message: str, task: str | None = None, starter_code: str | None = None, concept: str | None = None) -> TeacherResponse:
    return TeacherResponse(
        mode="task",
        message=message,
        task=task or "Write a small function that prints a greeting.",
        starter_code=starter_code or "def greet(name):\n    # add your code here\n    pass\n",
        rich_feedback=RichFeedback(
            what_worked="You are making progress.",
            what_to_fix="Try completing the missing implementation.",
            concept_gap=None,
            pattern_name=None,
            code_smell=None,
        ),
        concept_tested=concept or "variables",
        prerequisite_gap=None,
        level_suggestion=None,
    )


# ── Node 1: plan_lesson ───────────────────────────────────────────────────────

def plan_lesson(state: TeachState) -> dict:
    """
    Runs ONCE at session start.
    """
    try:
        plan = run_planner(state["topic"], state["level"])
    except Exception:
        plan = build_fallback_plan(state["topic"], state["level"])
    return {"lesson_plan": plan}


# ── Node 2: retrieve_context ──────────────────────────────────────────────────

def retrieve_context(state: TeachState) -> dict:
    """
    Fetches relevant material from the student's notes BEFORE giving a task.
    """
    # 1. Figure out current concept from lesson_plan
    lesson_plan = state["lesson_plan"]
    current_module_idx = state["current_module_idx"]
    
    concept = get_next_concept(lesson_plan, current_module_idx, state["profile"].model_dump())
    
    # 2. Use tools to get context
    material = search_student_notes.func(concept)
    task_history = get_task_history.func(concept)
    
    return {
        "retrieved_material": material,
        "retrieved_tasks": [task_history]
    }


# ── Node 3: give_task ─────────────────────────────────────────────────────────

def give_task(state: TeachState) -> dict:
    """
    Generates the next task for the student.
    """
    try:
        llm = get_llm_for_level(state["level"])
        chain = TEACH_PROMPT | llm | teacher_response_parser
        response = chain.invoke({
            "level": state["level"],
            "topic": state["topic"],
            "student_profile": json.dumps(state["profile"].model_dump()),
            "retrieved_context": state["retrieved_material"],
            "task_history": "\n".join(state["retrieved_tasks"] or ["No prior tasks yet."]),
            "format_instructions": teacher_response_parser.get_format_instructions(),
        })
    except Exception:
        response = build_fallback_response(
            state,
            message="Let’s build something small and concrete.",
            task="Write a function that returns the square of a number.",
            concept="functions",
        )
    
    return {
        "last_response": response,
        "task_count": state["task_count"] + 1,
        "conversation_history": [AIMessage(content=response.message)]
    }


# ── Node 4: evaluate_code ─────────────────────────────────────────────────────

def evaluate_code(state: TeachState) -> dict:
    """
    Evaluates the student's code submission.
    """
    try:
        llm = get_llm_for_level(state["level"])
        language = "java" if "java" in state["topic"].lower() else "python"
        execution_result = run_code_snippet.func(state["student_code"], language)
        chain = FEEDBACK_PROMPT | llm | teacher_response_parser
        concept = state["last_response"].concept_tested or "general"

        response = chain.invoke({
            "level": state["level"],
            "task": state["last_response"].task,
            "student_code": state["student_code"],
            "execution_result": execution_result,
            "expected_concept": concept,
            "format_instructions": teacher_response_parser.get_format_instructions(),
        })
    except Exception:
        concept = state["last_response"].concept_tested or "general"
        response = build_fallback_response(
            state,
            message="The implementation looks close; try one more pass and test it again.",
            task=state["last_response"].task if state["last_response"] else None,
            concept=concept,
        )
    
    updated_profile = state["profile"]
    # Determine correctness from the execution_result when possible.
    try:
        exec_text = str(execution_result or "").lower()
    except Exception:
        exec_text = ""

    error_indicators = ["error:\n", "could not run code", "traceback", "exception", "execution failed"]
    has_error = any(ind in exec_text for ind in error_indicators)

    # If execution produced no error we consider it correct, otherwise fall back to LLM judgment.
    is_correct = (not has_error) or (response.mode == "correct")
    updated_profile.update_after_task(concept, is_correct)
    
    return {
        "last_response": response,
        "profile": updated_profile,
        "level_suggestion": response.level_suggestion,
        "prereq_gap_detected": response.prerequisite_gap,
        "student_code": None,
        "conversation_history": [
            HumanMessage(content=state["student_code"]),
            AIMessage(content=response.message)
        ]
    }


# ── Node 5: handle_signal ─────────────────────────────────────────────────────

def handle_signal(state: TeachState) -> dict:
    """
    Handles student signals.
    """
    llm = get_llm_for_level(state["level"])
    
    # If it's a prereq gap detour
    try:
        if state["prereq_gap_detected"]:
            chain = DETOUR_PROMPT | llm | teacher_response_parser
            response = chain.invoke({
                "missing_concept": state["prereq_gap_detected"],
                "current_task": state["last_response"].task if state["last_response"] else "None",
                "level": state["level"],
                "format_instructions": teacher_response_parser.get_format_instructions(),
            })
        else:
            chain = SIGNAL_PROMPT | llm | teacher_response_parser
            response = chain.invoke({
                "signal": state["student_signal"],
                "signal_detail": state["signal_detail"],
                "current_task": state["last_response"].task if state["last_response"] else "None",
                "level": state["level"],
                "format_instructions": teacher_response_parser.get_format_instructions(),
            })
    except Exception:
        response = build_fallback_response(
            state,
            message="I’m simplifying the next step so you can keep moving.",
            task=state["last_response"].task if state["last_response"] else None,
            concept=state["last_response"].concept_tested if state["last_response"] else None,
        )
        
    return {
        "last_response": response,
        "student_signal": None,
        "signal_detail": None,
        "prereq_gap_detected": None,
        "conversation_history": [AIMessage(content=response.message)]
    }


# ── Node 6: check_prerequisites ───────────────────────────────────────────────

def prerequisite_check(state: TeachState) -> dict:
    """
    Checks if the student is ready for the upcoming task.
    """
    # Simply pass through if no lesson plan yet
    if not state["lesson_plan"]:
        return {"prereq_gap_detected": None}
        
    module = state["lesson_plan"].modules[state["current_module_idx"]]
    prereqs = module.prerequisites
    
    gaps = check_prerequisites.func(prereqs, json.dumps(state["profile"].concept_scores))
    
    if gaps != "No gaps found.":
        return {"prereq_gap_detected": gaps.split(", ")[0]} # Just handle one gap at a time
        
    return {"prereq_gap_detected": None}


# ── Node 7: update_profile ────────────────────────────────────────────────────

def update_profile(state: TeachState) -> dict:
    """
    Dedicated cleanup node that runs after evaluation.
    """
    analysis = analyse_performance(state["profile"].model_dump() | {"current_level": state["level"]})
    
    return {
        "level_suggestion": analysis["level_suggestion"]
    }


# ── Node 8: router hub ────────────────────────────────────────────────────────
def router_node(state: TeachState) -> dict:
    """
    Central hub node. Does nothing, just a junction for routing.
    """
    return {}


def route_decision(state: TeachState) -> str:
    """
    Pure logic — decides which node runs next.
    """
    if state.get("should_end_session"):
        return "end_session"
    if state.get("student_signal"):
        return "handle_signal"
    if state.get("student_code"):
        return "evaluate_code"
    if state.get("prereq_gap_detected"):
        return "handle_signal"
    if not state.get("lesson_plan"):
        return "plan_lesson"
    return "retrieve_context"


# ── Node 9: end_session ───────────────────────────────────────────────────────

def end_session(state: TeachState) -> dict:
    """
    Generates a session summary and saves it to disk.
    """
    # Simplified summary logic
    profile = state["profile"]
    summary = SessionSummary(
        date=datetime.now().strftime("%Y-%m-%d"),
        topic=state["topic"],
        level=state["level"],
        tasks_completed=state["task_count"],
        covered=list(profile.concept_scores.keys()),
        mastered=profile.strong_concepts,
        struggling=profile.weak_concepts,
        next_focus="More practice", # Placeholder
        concept_scores=profile.concept_scores
    )
    
    save_session(summary, state["topic"])
    return {"should_end_session": True}
