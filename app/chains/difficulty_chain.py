"""
app/chains/difficulty_chain.py
───────────────────────────────
LANGCHAIN CONCEPT: Chains with custom logic
────────────────────────────────────────────
Not every chain needs an LLM. Some chains are pure logic.
LangChain's RunnableLambda lets you wrap any Python function as a chain step.

This chain analyses the student's recent performance and decides:
  - Stay at current level
  - Suggest going up
  - Suggest going down
  - Which concept to focus on next

The logic here is rule-based (no LLM needed for this decision).
We use RunnableLambda to make it composable with LCEL if needed.

Docs to read:
  https://python.langchain.com/docs/concepts/runnables#runnable-lambda
"""

from config import (
    CONFIDENCE_STREAK_TO_LEVEL_UP,
    STRUGGLE_STREAK_TO_LEVEL_DOWN,
    CONCEPT_MASTERY_THRESHOLD,
    CONCEPT_WEAK_THRESHOLD
)

from langchain_core.runnables import RunnableLambda
from config import (
    CONFIDENCE_STREAK_TO_LEVEL_UP,
    STRUGGLE_STREAK_TO_LEVEL_DOWN,
    CONCEPT_MASTERY_THRESHOLD,
    CONCEPT_WEAK_THRESHOLD
)


def analyse_performance(profile_data: dict) -> dict:
    """
    Pure logic — analyses student profile and returns recommendations.
    """
    confidence_streak = profile_data.get("confidence_streak", 0)
    struggle_streak = profile_data.get("struggle_streak", 0)
    concept_scores = profile_data.get("concept_scores", {})
    current_level = profile_data.get("current_level", "beginner")
    
    level_suggestion = None
    if confidence_streak >= CONFIDENCE_STREAK_TO_LEVEL_UP and current_level != "advanced":
        level_suggestion = "up"
    elif struggle_streak >= STRUGGLE_STREAK_TO_LEVEL_DOWN and current_level != "beginner":
        level_suggestion = "down"
        
    focus_concepts = [c for c, s in concept_scores.items() if s <= CONCEPT_WEAK_THRESHOLD]
    ready_concepts = [c for c, s in concept_scores.items() if s >= CONCEPT_MASTERY_THRESHOLD]
    
    recommendation = ""
    if level_suggestion == "up":
        recommendation = "You're crushing it! Let's try more advanced tasks."
    elif level_suggestion == "down":
        recommendation = "This seems a bit tough. Let's revisit some basics to build confidence."
    elif focus_concepts:
        recommendation = f"Let's spend more time on {', '.join(focus_concepts)}."
    else:
        recommendation = "You're doing great. Let's keep going!"
        
    return {
        "level_suggestion": level_suggestion,
        "focus_concepts": focus_concepts,
        "ready_concepts": ready_concepts,
        "recommendation": recommendation
    }


def get_next_concept(lesson_plan, current_module_idx: int, profile_data: dict) -> str:
    """
    Decides which concept to focus on next.
    """
    if not lesson_plan or current_module_idx >= len(lesson_plan.modules):
        return "Complete"
        
    module = lesson_plan.modules[current_module_idx]
    concept_scores = profile_data.get("concept_scores", {})
    
    # 1. Check for weak concepts in current module
    weak_in_module = [c for c in module.concepts if concept_scores.get(c, 0.5) <= CONCEPT_WEAK_THRESHOLD]
    if weak_in_module:
        # Return the weakest one
        return min(weak_in_module, key=lambda c: concept_scores.get(c, 0.5))
        
    # 2. Check if all concepts in current module are mastered
    module_mastered = all(concept_scores.get(c, 0.0) >= CONCEPT_MASTERY_THRESHOLD for c in module.concepts)
    
    if module_mastered and current_module_idx + 1 < len(lesson_plan.modules):
        # Move to next module's first concept
        return lesson_plan.modules[current_module_idx + 1].concepts[0]
        
    # 3. Otherwise return the next un-mastered concept in current module
    for concept in module.concepts:
        if concept_scores.get(concept, 0.0) < CONCEPT_MASTERY_THRESHOLD:
            return concept
            
    return module.concepts[-1] # Fallback to last concept


difficulty_chain = RunnableLambda(analyse_performance)

