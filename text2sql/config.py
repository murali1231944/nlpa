"""
config.py — Central configuration for the NLP Text-to-SQL pipeline.

ALL tunable values live here (SDD Section 6). Never scatter magic numbers
in other modules. Thresholds are starting points; the human tunes them after
inspecting the linking logs in Phase 3.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# ── Locate the .env file (one level above this file, i.e. text2sql/.env) ──
_HERE = Path(__file__).parent          # text2sql/
load_dotenv(_HERE / ".env")

# ── Paths ──────────────────────────────────────────────────────────────────
# DB_PATH points to college.db inside the data/ folder (SDD §7.1)
DB_PATH = str(_HERE / "data" / "college.db")

EXAMPLES_PATH   = str(_HERE / "data" / "examples.json")
TEST_Q_PATH     = str(_HERE / "data" / "test_questions.json")
EMBED_FILE      = str(_HERE / "data" / "example_embeddings.npy")
CACHE_FILE      = str(_HERE / "data" / "llm_cache.json")
RESULTS_DIR     = str(_HERE / "data" / "results")

# ── LLM settings ───────────────────────────────────────────────────────────
# Groq credentials and model are read from .env (never hard-coded).
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

# Seconds to sleep after each REAL (non-cached) LLM call (SDD §6, §8.7).
# Prevents hitting free-tier rate limits.
LLM_CALL_DELAY  = float(os.getenv("LLM_CALL_DELAY", "1.0"))

# ── NLP / linking thresholds (SDD §6) ─────────────────────────────────────
# Minimum cosine similarity (0-1) for a schema link to be accepted.
# Tuned by inspecting scores_log in Phase 3.
SCHEMA_LINK_THRESHOLD = float(os.getenv("SCHEMA_LINK_THRESHOLD", "0.40"))

# Minimum rapidfuzz ratio (0-100) for a value link to be accepted.
# Tuned by inspecting fuzzy scores in Phase 3.
VALUE_LINK_THRESHOLD  = int(os.getenv("VALUE_LINK_THRESHOLD", "75"))

# Tokens shorter than this character count must match exactly (case-insensitive)
# to prevent false fuzzy matches on short words like "cse".
MIN_FUZZY_LEN = int(os.getenv("MIN_FUZZY_LEN", "4"))

# ── Retrieval ──────────────────────────────────────────────────────────────
# Number of similar solved examples to retrieve per question (SDD §6).
TOP_K_EXAMPLES = int(os.getenv("TOP_K_EXAMPLES", "4"))

# Sentence-transformers model used for schema linking and example retrieval
# (SDD §3 and §6). Loaded once at import time in each module that needs it.
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-MiniLM-L6-v2")

# ── Pipeline settings ──────────────────────────────────────────────────────
# Maximum self-correction retries when SQL fails execution (SDD §6).
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "1"))

# Maximum rows fetched from the database for display (SDD §6).
MAX_ROWS = int(os.getenv("MAX_ROWS", "500"))
