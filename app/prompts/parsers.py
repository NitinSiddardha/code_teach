"""
app/prompts/parsers.py
───────────────────────
LANGCHAIN CONCEPTS: Output Parsers + Structured Outputs
─────────────────────────────────────────────────────────
Right now in the artifact, JSON parsing is fragile — one extra word breaks it.
Output parsers + Pydantic models fix this permanently.

There are two things to learn here:

1. PYDANTIC MODELS — define the exact shape of what you want back from the LLM.
   The model MUST return data matching this shape. Validation is automatic.

2. LANGCHAIN OUTPUT PARSERS — wrap your Pydantic model so LangChain can:
   a. Tell the LLM exactly what format to respond in (format_instructions)
   b. Parse the response back into your Pydantic object automatically

How it connects to the app:
  - TeacherResponse  : what the agent returns after every task/evaluation
  - LessonPlan       : what the planner chain returns after reading the student's material
  - SessionSummary   : what gets saved at the end of each session
  - StudentProfile   : tracks competency scores, streaks, weak/strong concepts

Docs to read:
  https://python.langchain.com/docs/concepts/output_parsers
  https://python.langchain.com/docs/how_to/structured_output
"""

from typing import Optional, List, Literal, Dict
from pydantic import BaseModel, Field
from langchain_core.output_parsers import PydanticOutputParser
from config import CONCEPT_MASTERY_THRESHOLD, CONCEPT_WEAK_THRESHOLD


# ── Pydantic Models ───────────────────────────────────────────────────────────

class RichFeedback(BaseModel):
    """
    Detailed feedback on a code submission.
    """
    what_worked:  str            = Field(description="What the student did correctly, however small")
    what_to_fix:  Optional[str]  = Field(description="The ONE most important thing to fix")
    concept_gap:  Optional[str]  = Field(description="Did they get right answer the wrong way?")
    pattern_name: Optional[str]  = Field(description="Name of the pattern used, if any")
    code_smell:   Optional[str]  = Field(description="One readability note, intermediate/advanced only")


class TeacherResponse(BaseModel):
    """
    Every response from the teaching agent follows this shape.
    """
    mode: Literal["task", "correct", "almost", "stuck", "break_it", "micro_module", "level_adjust"] = Field(
        description="The type of response. 'task' = new task, 'correct' = they got it, etc."
    )
    message: str = Field(description="Short message, max 4 lines, no lectures")
    task:          Optional[str]  = Field(default=None, description="the task description (only for task/correct/break_it)")
    starter_code:  Optional[str]  = Field(default=None, description="scaffold code with TODOs (beginner/intermediate only)")
    rich_feedback: Optional[RichFeedback] = Field(default=None, description="detailed feedback (only when evaluating code)")
    concept_tested: Optional[str]  = Field(default=None, description="which concept this task covers (for tracking)")
    prerequisite_gap: Optional[str] = Field(default=None, description="if a prereq gap was detected, name it")
    level_suggestion: Optional[Literal["up", "down"]] = Field(default=None, description="suggest level change or None")


class Module(BaseModel):
    """A single module in the lesson plan."""
    title:       str       = Field(description="Module title")
    concepts:    List[str] = Field(description="Concepts covered in this module")
    task_count:  int       = Field(description="Estimated number of tasks")
    prerequisites: List[str] = Field(description="Concepts student needs before this module")


class LessonPlan(BaseModel):
    """
    Output of the planner chain.
    """
    topic:           str          = Field(description="the main topic")
    modules:         List[Module] = Field(description="ordered list of modules")
    total_tasks:     int          = Field(description="estimated total tasks")
    estimated_hours: float        = Field(description="rough time estimate")
    notes:           str          = Field(description="any special notes about this material")


class SessionSummary(BaseModel):
    """
    Saved at the end of every session.
    """
    date:            str       = Field(description="Current date")
    topic:           str       = Field(description="Lesson topic")
    level:           str       = Field(description="Student level")
    tasks_completed: int       = Field(description="Count of tasks finished")
    covered:         List[str] = Field(description="concepts covered this session")
    mastered:        List[str] = Field(description="concepts with score > MASTERY_THRESHOLD")
    struggling:      List[str] = Field(description="concepts with score < WEAK_THRESHOLD")
    next_focus:      str       = Field(description="what to work on next session")
    concept_scores:  Dict[str, float] = Field(description="full score map to carry forward")


class StudentProfile(BaseModel):
    """
    Live profile updated after every task.
    """
    declared_level:     str   = "beginner"
    inferred_level:     str   = "beginner"
    concept_scores:     Dict[str, float]  = Field(default_factory=dict)
    avg_attempts:       float = 1.0
    total_tasks:        int   = 0
    total_attempts:     int   = 0
    struggle_streak:    int   = 0
    confidence_streak:  int   = 0
    weak_concepts:      List[str] = Field(default_factory=list)
    strong_concepts:    List[str] = Field(default_factory=list)

    def update_after_task(self, concept: str, is_correct: bool):
        """
        Called after every submission.
        """
        if concept not in self.concept_scores:
            self.concept_scores[concept] = 0.5 # Start at neutral
            
        if is_correct:
            self.concept_scores[concept] = min(1.0, self.concept_scores[concept] + 0.15)
            self.confidence_streak += 1
            self.struggle_streak = 0
        else:
            self.concept_scores[concept] = max(0.0, self.concept_scores[concept] - 0.1)
            self.struggle_streak += 1
            self.confidence_streak = 0
            
        self.total_tasks += 1
        self.total_attempts += 1 # In this simple model, 1 submission = 1 attempt
        self.avg_attempts = self.total_attempts / self.total_tasks
        
        # Rebuild weak and strong concepts
        self.weak_concepts = [c for c, s in self.concept_scores.items() if s <= CONCEPT_WEAK_THRESHOLD]
        self.strong_concepts = [c for c, s in self.concept_scores.items() if s >= CONCEPT_MASTERY_THRESHOLD]


# ── Create output parsers ─────────────────────────────────────────────────────
teacher_response_parser = PydanticOutputParser(pydantic_object=TeacherResponse)
lesson_plan_parser      = PydanticOutputParser(pydantic_object=LessonPlan)
session_summary_parser  = PydanticOutputParser(pydantic_object=SessionSummary)

# ── Assessment Models ───────────────────────────────────────────────────────
class AssessmentQuestion(BaseModel):
    question: str
    options: List[str]
    difficulty: Optional[Literal["easy", "medium", "hard"]] = "medium"
    correct_option: Optional[int] = Field(default=None, description="Hidden index of the correct answer")
    selected_option: Optional[int] = Field(default=None, description="Student-selected option index")

    model_config = {
        "extra": "ignore"
    }


class AssessmentQuiz(BaseModel):
    topic: str
    level: str
    questions: List[AssessmentQuestion]

    model_config = {
        "extra": "ignore"
    }


assessment_parser = PydanticOutputParser(pydantic_object=AssessmentQuiz)

