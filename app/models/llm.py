"""
app/models/llm.py
─────────────────
LANGCHAIN CONCEPT: LLM Wrappers & Chat Models
─────────────────────────────────────────────
LangChain wraps raw API calls into a standard interface.
This means you can swap Claude for GPT-4 or Gemini by changing one line.

In code.teach we use TWO models intentionally:
  - fast_llm   : Claude Haiku  — evaluating beginner code (cheap, fast, good enough)
  - smart_llm  : Claude Sonnet — lesson planning, rich feedback, advanced students

Both are ChatModels — they take a list of messages and return a message.
This is different from a plain LLM which takes a string and returns a string.
Use ChatModels for everything in modern LangChain.

What you need to fill in:
  - Import ChatAnthropic from langchain_anthropic
  - Instantiate fast_llm and smart_llm using the model names from config.py
  - Both should have temperature=0.7 (some creativity but not too random)
  - smart_llm can have a slightly higher temperature (0.9) for richer responses

Docs to read first:
  https://python.langchain.com/docs/integrations/chat/anthropic
"""

from config import GOOGLE_API_KEY, FAST_MODEL, SMART_MODEL
from langchain_google_genai import ChatGoogleGenerativeAI

# ── Create fast_llm ─────────────────────────────────────────────────────────
# Used for: evaluating beginner/intermediate code submissions
# Should be: ChatGoogleGenerativeAI with FAST_MODEL, temperature=0.7
fast_llm = ChatGoogleGenerativeAI(
    model=FAST_MODEL,
    temperature=0.7,
    google_api_key=GOOGLE_API_KEY
)


# ── Create smart_llm ────────────────────────────────────────────────────────
# Used for: lesson planning, rich feedback, detour modules, advanced students
# Should be: ChatGoogleGenerativeAI with SMART_MODEL, temperature=0.9
smart_llm = ChatGoogleGenerativeAI(
    model=SMART_MODEL,
    temperature=0.9,
    google_api_key=GOOGLE_API_KEY
)


def get_llm_for_level(level: str):
    """
    Returns the appropriate LLM based on student level.
    
    - beginner      → fast_llm (simple eval is enough)
    - intermediate  → fast_llm
    - advanced      → smart_llm (nuanced feedback needed)
    """
    if level == "advanced":
        return smart_llm
    return fast_llm

