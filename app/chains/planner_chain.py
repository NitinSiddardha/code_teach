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
from app.prompts.templates import PLANNER_PROMPT, TOPIC_ANALYSIS_PROMPT
from app.prompts.parsers import (
    LessonPlan,
    lesson_plan_parser,
    assessment_parser,
    topic_metadata_parser,
    TopicMetadata,
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


def detect_topic_metadata(topic: str) -> TopicMetadata:
    """Use an LLM prompt to detect programming language and concept from raw topic text."""
    text = (topic or "").strip() or "programming basics"
    try:
        chain = TOPIC_ANALYSIS_PROMPT | smart_llm | topic_metadata_parser
        metadata = chain.invoke({
            "topic": text,
            "format_instructions": topic_metadata_parser.get_format_instructions()
        })
        if not metadata.concept:
            metadata.concept = text
        return metadata
    except Exception:
        return TopicMetadata(language=None, concept=text)


def run_planner(topic: str, level: str, previous_session=None, student_profile: dict | None = None, topic_meta: TopicMetadata | None = None) -> LessonPlan:
    """
    Runs the planner chain to generate a lesson plan.
    Called once at the start of each session.
    """
    material = get_material_summary() or "No material uploaded"
    profile_text = json.dumps(student_profile or {})
    
    if topic_meta is None:
        topic_meta = detect_topic_metadata(topic)

    chain = build_planner_chain()
    plan = chain.invoke({
        "topic": topic,
        "level": level,
        "language": topic_meta.language or "",
        "concept": topic_meta.concept or topic,
        "material": material,
        "previous_session": str(previous_session) if previous_session else "First session",
        "student_profile": profile_text,
        "format_instructions": lesson_plan_parser.get_format_instructions()
    })
    return plan


def build_assessment_fallback(topic_clean: str, level: str, topic_meta: TopicMetadata | None = None) -> AssessmentQuiz:
    """Build a generic fallback assessment when the LLM output is missing or invalid."""
    language = (topic_meta.language or "").strip()
    concept = (topic_meta.concept or topic_clean).strip()
    base_prefix = f"In {language}, " if language else ""
    question_text = concept or "the requested topic"

    q1 = AssessmentQuestion(
        question=f"{base_prefix}what is the main purpose of {question_text}?",
        options=[
            f"To practice {question_text}",
            "To connect to the internet",
            "To build a website layout",
            "To manage a database",
        ],
        difficulty="easy",
        correct_option=0,
    )
    q2 = AssessmentQuestion(
        question=f"Which example best matches the concept of {question_text}?",
        options=[
            f"A code statement that demonstrates {question_text}",
            "A sentence about sports",
            "A picture of a cat",
            "A math formula unrelated to code",
        ],
        difficulty="medium",
        correct_option=0,
    )
    q3 = AssessmentQuestion(
        question=f"{base_prefix}Which statement is true about {question_text}?",
        options=[
            f"It is a core programming concept.",
            "It is a type of dessert.",
            "It is a music genre.",
            "It is a weather condition.",
        ],
        difficulty="medium",
        correct_option=0,
    )

    return AssessmentQuiz(topic=topic_clean, level=level, questions=[q1, q2, q3])


def run_assessment(topic: str, level: str, conversation: str = ""):
    """
    Generates a short diagnostic quiz tailored to topic/level and conversation context.
    Returns an AssessmentQuiz Pydantic object.
    """
    topic_meta = detect_topic_metadata(topic)
    topic_clean = topic_meta.concept or (topic or "").strip().title()

    try:
        chain = ASSESSMENT_PROMPT | smart_llm | assessment_parser
        quiz = chain.invoke({
            "topic": topic,
            "language": topic_meta.language or "",
            "concept": topic_meta.concept or topic_clean,
            "level": level,
            "conversation": conversation or "",
            "format_instructions": assessment_parser.get_format_instructions()
        })
        # Post-process quiz to ensure topic and difficulty align with inputs
        try:
            quiz.topic = topic_clean
            level_map = {"beginner": "easy", "intermediate": "medium", "advanced": "hard"}
            target_diff = level_map.get(level, "medium")
            for q in quiz.questions:
                if not getattr(q, "difficulty", None):
                    q.difficulty = target_diff
                if q.correct_option is None:
                    q.correct_option = 0
            if not quiz.questions:
                return build_assessment_fallback(topic_clean, level, topic_meta)
            return quiz
        except Exception:
            return quiz
    except Exception:
        return build_assessment_fallback(topic_clean, level, topic_meta)


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

