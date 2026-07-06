"""
config.py — App-wide settings and constants.
Load environment variables and define model names, paths, thresholds here.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── API Keys ──────────────────────────────────────────────────────────────────

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# ── Model names ───────────────────────────────────────────────────────────────
# You will use these in app/models/llm.py when creating LLM wrappers.
# We use two models on purpose:
#   - FAST_MODEL  : cheap, quick — for evaluating beginner code (low stakes)
#   - SMART_MODEL : more capable — for planning, advanced feedback, detours

FAST_MODEL  = "gemini-1.5-flash"
SMART_MODEL = "gemini-1.5-pro"


# ── Paths ─────────────────────────────────────────────────────────────────────

DATA_DIR     = "data"
SESSIONS_DIR = "data/sessions"
UPLOADS_DIR  = "data/uploads"
VECTOR_DIR   = "data/vectorstore"   # where Chroma will persist its DB

# ── Teaching thresholds ───────────────────────────────────────────────────────
# These drive the dynamic behaviour of the agent.
# When you build difficulty_chain.py, these are the numbers it checks against.

CONFIDENCE_STREAK_TO_LEVEL_UP = 4   # 4 correct in a row → suggest level up
STRUGGLE_STREAK_TO_LEVEL_DOWN = 3   # 3 stuck/almost in a row → suggest level down
CONCEPT_MASTERY_THRESHOLD     = 0.8  # score >= 0.8 → concept is "mastered"
CONCEPT_WEAK_THRESHOLD        = 0.4  # score <= 0.4 → concept is "struggling"

# ── Retrieval ─────────────────────────────────────────────────────────────────

CHUNK_SIZE    = 500   # characters per chunk when splitting uploaded material
CHUNK_OVERLAP = 50    # overlap between chunks so context isn't lost at boundaries
TOP_K_RESULTS = 4     # how many chunks to retrieve per query
