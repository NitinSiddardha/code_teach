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

import json

from app.models.llm import smart_llm
from app.prompts.templates import PLANNER_PROMPT
from app.prompts.parsers import (
    LessonPlan,
    lesson_plan_parser,
    assessment_parser,
    StudentProfile,
    AssessmentQuiz,
    AssessmentQuestion,
)
from app.prompts.templates import ASSESSMENT_PROMPT
from app.retrieval.vector_store import load_lesson_store


def build_planner_chain():
    """
    Builds and returns the lesson planner chain.
    """
    return PLANNER_PROMPT | smart_llm | lesson_plan_parser


def run_planner(topic: str, level: str, previous_session=None, student_profile: dict | None = None) -> LessonPlan:
    """
    Runs the planner chain to generate a lesson plan.
    Called once at the start of each session.
    """
    material = get_material_summary() or "No material uploaded"
    profile_text = json.dumps(student_profile or {})
    
    chain = build_planner_chain()
    plan = chain.invoke({
        "topic": topic,
        "level": level,
        "material": material,
        "previous_session": str(previous_session) if previous_session else "First session",
        "student_profile": profile_text,
        "format_instructions": lesson_plan_parser.get_format_instructions()
    })
    return plan


def build_assessment_fallback(topic_clean: str, level: str) -> AssessmentQuiz:
    """Build a topic-aware fallback assessment when the LLM output is missing or invalid."""
    lower = topic_clean.lower()
    if "c++" in lower or "cpp" in lower:
        q1 = AssessmentQuestion(
            question="In C++, which type is best for storing whole numbers?",
            options=["int", "string", "double", "bool"],
            difficulty="easy",
            correct_option=0,
        )
        q2 = AssessmentQuestion(
            question="How do you declare a variable named count with value 10 in C++?",
            options=["int count = 10;", "count := 10", "let count = 10", "count = 10"],
            difficulty="easy",
            correct_option=0,
        )
        q3 = AssessmentQuestion(
            question="Which symbol ends a statement in C++?",
            options=[";", ".", ",", ":"],
            difficulty="easy",
            correct_option=0,
        )
    elif "java" in lower:
        q1 = AssessmentQuestion(
            question="In Java, which keyword declares an integer variable?",
            options=["int", "var", "let", "string"],
            difficulty="easy",
            correct_option=0,
        )
        q2 = AssessmentQuestion(
            question="Which symbol ends a Java statement?",
            options=[";", ".", ",", ":"],
            difficulty="easy",
            correct_option=0,
        )
        q3 = AssessmentQuestion(
            question="What is the default value of an uninitialized int field in a Java class?",
            options=["0", "null", "undefined", "1"],
            difficulty="medium",
            correct_option=0,
        )
    elif "python" in lower:
        q1 = AssessmentQuestion(
            question="In Python, how do you create a variable named x with value 5?",
            options=["x = 5", "int x = 5", "let x = 5", "x := 5"],
            difficulty="easy",
            correct_option=0,
        )
        q2 = AssessmentQuestion(
            question="Which type in Python can hold multiple values?",
            options=["list", "int", "float", "bool"],
            difficulty="easy",
            correct_option=0,
        )
        q3 = AssessmentQuestion(
            question="What is a variable in Python?",
            options=["A container for storing a value", "A function", "A loop", "A comment"],
            difficulty="easy",
            correct_option=0,
        )
    else:
        q1 = AssessmentQuestion(
            question=f"What is most important to understand about {topic_clean}?",
            options=["The core concept", "The weather", "The menu", "The furniture"],
            difficulty="medium",
            correct_option=0,
        )
        q2 = AssessmentQuestion(
            question=f"Which of these is most closely related to {topic_clean}?",
            options=["The topic itself", "A random example", "A homework assignment", "A travel plan"],
            difficulty="medium",
            correct_option=0,
        )
        q3 = AssessmentQuestion(
            question=f"Which answer best shows understanding of {topic_clean}?",
            options=["A correct definition", "A wrong fact", "A joke", "A song"],
            difficulty="medium",
            correct_option=0,
        )

    return AssessmentQuiz(topic=topic_clean, level=level, questions=[q1, q2, q3])


def run_assessment(topic: str, level: str, conversation: str = ""):
    """
    Generates a short diagnostic quiz tailored to topic/level and conversation context.
    Returns an AssessmentQuiz Pydantic object.
    """
    # Normalize topic for clarity (e.g., handle c++ / cpp variants)
    t_raw = (topic or "").strip()
    t_low = t_raw.lower()
    if "c++" in t_low or "cpp" in t_low:
        topic_clean = "C++ Variables" if "variable" in t_low else "C++"
    elif "java" in t_low:
        topic_clean = "Java " + ("Variables" if "variable" in t_low else "Basics")
    elif "python" in t_low:
        topic_clean = "Python " + ("Variables" if "variable" in t_low else "Basics")
    else:
        # Capitalize each word as a safe default
        topic_clean = " ".join([w.capitalize() for w in t_raw.split()]) or topic

    try:
        chain = ASSESSMENT_PROMPT | smart_llm | assessment_parser
        quiz = chain.invoke({
            "topic": topic_clean,
            "level": level,
            "conversation": conversation or "",
            "format_instructions": assessment_parser.get_format_instructions()
        })
        # Post-process quiz to ensure topic and difficulty align with inputs
        try:
            # force the canonical topic
            quiz.topic = topic_clean
            # Map level to difficulty
            level_map = {"beginner": "easy", "intermediate": "medium", "advanced": "hard"}
            target_diff = level_map.get(level, "medium")
            for q in quiz.questions:
                # Ensure difficulty is set appropriately
                if not getattr(q, "difficulty", None):
                    q.difficulty = target_diff
                if q.correct_option is None:
                    q.correct_option = 0
                # If the question mentions another language, replace it with the cleaned topic's language
                q_text = q.question
                if "python" in q_text.lower() and "c++" in topic_clean.lower():
                    q.question = q_text.replace("Python", "C++").replace("python", "C++")
                if "python" in q_text.lower() and "java" in topic_clean.lower():
                    q.question = q_text.replace("Python", "Java").replace("python", "Java")
            if not quiz.questions:
                return build_assessment_fallback(topic_clean, level)
            return quiz
        except Exception:
            return quiz
    except Exception:
        return build_assessment_fallback(topic_clean, level)


def score_assessment(quiz_data) -> StudentProfile:
    """
    Convert assessment answers into an initial StudentProfile.
    """
    quiz = None
    if isinstance(quiz_data, dict):
        try:
            quiz = AssessmentQuiz.model_validate(quiz_data)
        except Exception:
            quiz = None
    elif isinstance(quiz_data, AssessmentQuiz):
        quiz = quiz_data

    if not quiz:
        return StudentProfile(declared_level="beginner", inferred_level="beginner")

    total = len(quiz.questions)
    correct = 0
    for question in quiz.questions:
        if question.correct_option is not None and question.selected_option is not None:
            if question.selected_option == question.correct_option:
                correct += 1

    score = 0.5
    if total > 0:
        score = 0.3 + 0.7 * (correct / total)

    concept_scores = {quiz.topic: round(score, 2)}
    confidence_streak = correct
    struggle_streak = total - correct

    profile = StudentProfile(
        declared_level=quiz.level,
        inferred_level=quiz.level,
        concept_scores=concept_scores,
        avg_attempts=1.0 if total > 0 else 0.0,
        total_tasks=total,
        total_attempts=total,
        struggle_streak=struggle_streak,
        confidence_streak=confidence_streak,
    )
    profile.weak_concepts = [k for k, v in profile.concept_scores.items() if v <= 0.4]
    profile.strong_concepts = [k for k, v in profile.concept_scores.items() if v >= 0.8]
    return profile


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

