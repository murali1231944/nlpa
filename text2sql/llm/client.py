"""
client.py — Groq chat-completion client with disk caching and SQL sanitization.

Handles:
  - Cache lookup by sha256(model + prompt) stored in data/llm_cache.json
  - Groq chat-completion SDK invocation
  - Transient error retries with exponential backoff
  - Rate-limit pacing (LLM_CALL_DELAY sleep after real calls)
  - Strict SQL output sanitization (strip markdown fences, labels, keep first statement)
  - Zero leakage of API key
"""

import hashlib
import json
import re
import time
from pathlib import Path

from text2sql.config import (
    CACHE_FILE,
    GROQ_API_KEY,
    GROQ_MODEL,
    LLM_CALL_DELAY,
)


def _compute_cache_key(model: str, prompt: str) -> str:
    """Compute sha256 hash of model name + prompt."""
    payload = f"{model}:{prompt}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_cache() -> dict[str, str]:
    """Load cached LLM responses from CACHE_FILE."""
    cache_path = Path(CACHE_FILE)
    if not cache_path.exists():
        return {}
    try:
        with open(cache_path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_cache(cache: dict[str, str]) -> None:
    """Save cache dictionary to CACHE_FILE."""
    cache_path = Path(CACHE_FILE)
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def clean_sql(raw: str) -> str:
    """
    Sanitize raw LLM output into clean, single-statement SQL (SDD §8.7).

    Steps:
      1. Remove markdown code fences (```sql ... ```)
      2. Remove leading label (e.g. 'sql:', 'SQL')
      3. Keep only the first statement
      4. Ensure exactly one trailing semicolon
    """
    text = raw.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove opening ```...
        lines = lines[1:] if len(lines) > 1 else []
        # Remove closing ``` if present
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    # Clean any loose backticks or code tags
    text = re.sub(r"^```[a-zA-Z]*\n?", "", text).strip()
    text = re.sub(r"\n?```$", "", text).strip()

    # Strip leading label like "sql:" or "SQL:" or "sql\n"
    text = re.sub(r"^(?:sql\s*:|sql)\s*", "", text, flags=re.IGNORECASE).strip()

    # Keep only the first statement if multiple statements separated by semicolon
    if ";" in text:
        text = text.split(";")[0].strip()

    # Ensure single trailing semicolon
    if text and not text.endswith(";"):
        text += ";"

    return text


def generate_sql(prompt: str, bypass_cache: bool = False) -> str:
    """
    Generate SQL for a prompt using Groq, consulting disk cache first.

    Args:
        prompt: The complete formatted prompt string.
        bypass_cache: If True, ignore existing cache entry and make a real call.

    Returns:
        Cleaned SQL query ending with a semicolon.

    Raises:
        RuntimeError: If GROQ_API_KEY is missing.
        Exception: If the API call fails after retries.
    """
    cache_key = _compute_cache_key(GROQ_MODEL, prompt)
    cache = _load_cache()

    if not bypass_cache and cache_key in cache:
        return cache[cache_key]

    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set in text2sql/.env. Configure it before making live LLM calls."
        )

    # Import Groq only when a cache miss requires a live call.
    try:
        from groq import Groq
    except ImportError as e:
        raise RuntimeError("Groq SDK is not installed. Run: pip install groq") from e

    client = Groq(api_key=GROQ_API_KEY, timeout=30.0, max_retries=0)

    # Exponential backoff on transient errors (up to 3 retries)
    max_attempts = 3
    last_err = None
    raw_text = ""

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=1,
                max_completion_tokens=2048,
                top_p=1,
                reasoning_effort="medium",
                stream=False,
            )
            raw_text = response.choices[0].message.content or ""
            if not raw_text.strip():
                raise RuntimeError("Groq returned an empty response.")
            break
        except Exception as err:
            last_err = err
            if attempt < max_attempts:
                time.sleep(2 ** (attempt - 1))  # 1s, 2s
            else:
                safe_error = str(last_err).replace(GROQ_API_KEY, "[REDACTED]")
                raise RuntimeError(
                    f"Groq API call failed after {max_attempts} attempts: {safe_error}"
                ) from last_err

    # Pacing sleep after real call (SDD §8.7)
    time.sleep(LLM_CALL_DELAY)

    cleaned = clean_sql(raw_text)

    # Save to disk cache
    cache[cache_key] = cleaned
    _save_cache(cache)

    return cleaned
