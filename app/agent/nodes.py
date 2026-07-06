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


def fallback_task_for_topic(topic_language: str | None = None, concept: str | None = None) -> str:
    language = (topic_language or "").lower()
    is_variable = concept and "variable" in concept.lower()
    is_function = concept and "function" in concept.lower()
    concept_text = concept or "the requested concept"

    if language == "c++" or language == "cpp":
        base = "In C++,"
    elif language == "java":
        base = "In Java,"
    elif language == "python":
        base = "In Python,"
    else:
        base = ""

    if is_variable:
        return f"{base} declare a variable named count and assign it the value 10."
    if is_function:
        return f"{base} write a function named square that returns the square of a number."
    return f"{base} write a small code example that demonstrates {concept_text}.".strip()


def get_starter_code(language: str, concept: str | None = None) -> str:
    if language in {"c++", "cpp"}:
        if concept and "variable" in concept.lower():
            return "#include <iostream>\nint main() {\n    int count = 10;\n    std::cout << count << std::endl;\n    return 0;\n}\n"
        return "#include <iostream>\nint square(int x) {\n    return x * x;\n}\nint main() {\n    std::cout << square(5) << std::endl;\n    return 0;\n}\n"
    if language == "java":
        if concept and "variable" in concept.lower():
            return "public class Main {\n    public static void main(String[] args) {\n        int count = 10;\n        System.out.println(count);\n    }\n}\n"
        return "public class Main {\n    public static int square(int x) {\n        return x * x;\n    }\n    public static void main(String[] args) {\n        System.out.println(square(5));\n    }\n}\n"
    if language == "python":
        if concept and "variable" in concept.lower():
            return "count = 10\nprint(count)\n"
        return "def square(x):\n    return x * x\n\nprint(square(5))\n"
    return "def greet(name):\n    # add your code here\n    pass\n"


def build_fallback_response(state: TeachState, *, message: str, task: str | None = None, starter_code: str | None = None, concept: str | None = None) -> TeacherResponse:
    language = (state.get("topic_language") or "python").lower()
    if language == "c++":
        language = "cpp"
    return TeacherResponse(
        mode="task",
        message=message,
        task=task or "Write a small task that practices the concept.",
        starter_code=starter_code or get_starter_code(language, concept),
        rich_feedback=RichFeedback(
            what_worked="You are making progress.",
            what_to_fix="Try completing the missing implementation.",
            concept_gap=None,
            pattern_name=None,
            code_smell=None,
        ),
        concept_tested=concept or (state.get("topic_concept") or "general"),
        prerequisite_gap=None,
        level_suggestion=None,
    )


# ── Node 1: plan_lesson ───────────────────────────────────────────────────────

def plan_lesson(state: TeachState) -> dict:
    """
    Runs ONCE at session start.
    """
    try:
        profile_data = state["profile"].model_dump() if state.get("profile") else None
        topic_meta = None
        if state.get("topic_language") or state.get("topic_concept"):
            from app.prompts.parsers import TopicMetadata
            topic_meta = TopicMetadata(
                language=state.get("topic_language"),
                concept=state.get("topic_concept"),
            )
        plan = run_planner(state["topic"], state["level"], student_profile=profile_data, topic_meta=topic_meta)
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
        "retrieved_tasks": [task_history],
        "current_concept": concept
    }


# ── Node 3: give_task ─────────────────────────────────────────────────────────

def give_task(state: TeachState) -> dict:
    """
    Generates the next task for the student.
    """
    try:
        llm = get_llm_for_level(state["level"])
        chain = TEACH_PROMPT | llm | teacher_response_parser
        concept = state.get("current_concept") or "general"
        response = chain.invoke({
            "level": state["level"],
            "topic": state["topic"],
            "language": state.get("topic_language") or "",
            "concept": concept,
            "student_profile": json.dumps(state["profile"].model_dump()),
            "retrieved_context": state["retrieved_material"],
            "task_history": "\n".join(state["retrieved_tasks"] or ["No prior tasks yet."]),
            "format_instructions": teacher_response_parser.get_format_instructions(),
        })
    except Exception:
        concept = state.get("current_concept") or state.get("topic_concept") or "general"
        response = build_fallback_response(
            state,
            message="Let’s build something small and concrete.",
            task=fallback_task_for_topic(state.get("topic_language"), concept),
            concept=concept,
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
        language = (state.get("topic_language") or "python").lower()
        if language == "c++":
            language = "cpp"

        # Simple heuristic to detect submitted code language; if it doesn't match
        # the expected language, ask the student to resubmit in the target language.
        submitted = (state.get("student_code") or "").strip()
        def detect_lang(code: str) -> str:
            c = code.strip()
            if c.startswith("#include") or "std::" in c or "cout" in c or "int main" in c:
                return "cpp"
            if c.startswith("public static") or "System.out" in c or ("class " in c and "{" in c):
                return "java"
            if c.startswith("def ") or c.startswith("import ") or "print(" in c:
                return "python"
            if "console.log(" in c or c.startswith("function ") or c.strip().endswith(";") and "=>" in c:
                return "javascript"
            if c.strip().startswith("package main") or "func main" in c:
                return "go"
            if c.strip().startswith("<?php") or c.strip().startswith("echo "):
                return "php"
            if c.strip().startswith("using System") or "Console.WriteLine" in c:
                return "csharp"
            if c.strip().startswith("#") and "include" in c and ("<stdio.h>" in c or "printf(" in c):
                return "c"
            if c.strip().startswith("def ") and c.strip().endswith("end"):
                return "ruby"
            if ":" in c and ("=>" in c or "interface" in c):
                return "typescript"
            return "unknown"

        detected = detect_lang(submitted)
        if detected != "unknown" and detected != language:
            # Build a gentle instructive response asking for the correct language
            hint = None
            if language in {"cpp", "c++"}:
                hint = "Please submit your solution in C++ (e.g., include <iostream> and use int main)."
            elif language == "java":
                hint = "Please submit your solution in Java (e.g., a class with a main method)."
            elif language == "python":
                hint = "Please submit your solution in Python."
            else:
                hint = f"Please submit your solution in {language.title()} if possible."

            response = build_fallback_response(
                state,
                message=f"It looks like you submitted code in a different language. {hint}",
                task=state["last_response"].task if state.get("last_response") else None,
                concept=state["last_response"].concept_tested if state.get("last_response") else state.get("topic_concept"),
            )
            updated_profile = state["profile"]
            # Do not mark as incorrect; prompt for correct language instead
            return {
                "last_response": response,
                "profile": updated_profile,
                "level_suggestion": response.level_suggestion,
                "prereq_gap_detected": response.prerequisite_gap,
                "student_code": state.get("student_code"),
                "conversation_history": [
                    HumanMessage(content=state.get("student_code") or ""),
                    AIMessage(content=response.message)
                ]
            }

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

    current_module_idx = state.get("current_module_idx", 0)
    current_task_idx = state.get("current_task_idx", 0)
    lesson_plan = state.get("lesson_plan")
    next_module_idx = current_module_idx
    next_task_idx = current_task_idx
    if is_correct and lesson_plan and lesson_plan.modules:
        module = lesson_plan.modules[current_module_idx]
        if current_task_idx + 1 >= module.task_count:
            next_module_idx = min(current_module_idx + 1, len(lesson_plan.modules) - 1)
            next_task_idx = 0
        else:
            next_task_idx = current_task_idx + 1

    return {
        "last_response": response,
        "profile": updated_profile,
        "level_suggestion": response.level_suggestion,
        "prereq_gap_detected": response.prerequisite_gap,
        "student_code": None,
        "current_module_idx": next_module_idx,
        "current_task_idx": next_task_idx,
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
