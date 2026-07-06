"""
app/prompts/templates.py
─────────────────────────
LANGCHAIN CONCEPT: Prompt Templates
─────────────────────────────────────
Instead of hardcoded strings, PromptTemplates are reusable prompts with variables.
You define the template once. You fill in variables at runtime.

Why this matters in code.teach:
  - Same teaching logic, different topic/level/material every time
  - Swapping the topic doesn't mean rewriting the prompt
  - format_instructions from your output parsers plug in here automatically

Two types you'll use:
  1. PromptTemplate         — for simple string prompts
  2. ChatPromptTemplate     — for chat-style prompts (system + human messages)
                              Use this for everything in code.teach

How they're used in this app:
  TEACH_PROMPT    → used by the teaching agent every loop iteration
  PLANNER_PROMPT  → used by planner_chain.py once at the start
  FEEDBACK_PROMPT → used when evaluating submitted code
  DETOUR_PROMPT   → used when a prerequisite gap is detected

Docs to read:
  https://python.langchain.com/docs/concepts/prompt_templates
"""

from langchain_core.prompts import ChatPromptTemplate


# ── TEACH_PROMPT ──────────────────────────────────────────────────────────────
# Used by: teacher_agent.py → give_task node
TEACH_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a hands-on coding teacher. 
Your philosophy: learn by doing, one tiny task at a time.
Scaffold rules:
- Beginner: Lead them by the hand, provide heavy scaffold.
- Intermediate: Provide some starter code, let them do the core logic.
- Advanced: Just give the task, no scaffold unless requested.

Tone: A senior developer sitting next to them, encouraging and technical but concise.
Rules:
1. Max 4 lines in your 'message' field.
2. NO long lectures or explanations unless they ask.
3. Every response MUST include a 'task' or 'correct' assessment.

{format_instructions}"""),
    ("human", """Subject: {topic}
Current Level: {level}
Student Profile: {student_profile}

Relevant context from notes:
{retrieved_context}

Task History:
{task_history}

Please provide the next task or respond to the student's submission.""")
])


# ── FEEDBACK_PROMPT ───────────────────────────────────────────────────────────
# Used by: teacher_agent.py → evaluate node
FEEDBACK_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an expert code reviewer and teacher.
Evaluate the student's code submission against the task provided.
Be encouraging but precise.

{format_instructions}"""),
    ("human", """Level: {level}
Task: {task}
Submitted Code:
{student_code}

Execution Output:
{execution_result}

Expected Concept: {expected_concept}

Evaluate this submission. If it's correct, explain why. If not, point out the ONE most important thing to fix.""")
])


# ── PLANNER_PROMPT ────────────────────────────────────────────────────────────
# Used by: planner_chain.py → runs ONCE at session start
PLANNER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a curriculum designer. 
Generate a structured lesson plan based on the student's uploaded material and current level.
The plan should have 5-8 modules, ordered logically.

{format_instructions}"""),
    ("human", """Topic: {topic}
Level: {level}
Material Summary: {material}
Previous Session: {previous_session}

Create a lesson plan that grounds the teaching in the provided material.""")
])


# ── DETOUR_PROMPT ─────────────────────────────────────────────────────────────
# Used by: teacher_agent.py → prerequisite_check node
DETOUR_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You detected a prerequisite gap. 
Briefly teach the missing concept {missing_concept} before returning to the main task.
Keep it very short.

{format_instructions}"""),
    ("human", """Missing Concept: {missing_concept}
Current Task we were on: {current_task}
Level: {level}

Provide a micro-module to fix this gap.""")
])


# ── SIGNAL_PROMPT ─────────────────────────────────────────────────────────────
# Used by: teacher_agent.py → handle_signal node
SIGNAL_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """The student sent a signal about their progress. 
Adjust your teaching according to the signal:
- too_hard: simplify, step back.
- too_easy: jump ahead, more challenge.
- lost_concept: micro-explain the concept.
- more_practice: give another task on the same concept.
- missing_concept: teach the requested concept.

{format_instructions}"""),
    ("human", """Signal: {signal}
Detail: {signal_detail}
Current Task: {current_task}
Level: {level}

Please respond to this signal.""")
])

