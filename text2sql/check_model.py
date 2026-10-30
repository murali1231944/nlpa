"""
check_model.py — Phase 1 model verification script (SDD §14 Phase 1).

This script:
  (a) Lists models available to your Groq API key.
  (b) Makes one test call with the model in GROQ_MODEL.

If the configured model is not available, it prints the list and STOPS.
It never switches models silently.

Run: python text2sql/check_model.py
"""

import sys
import time
from pathlib import Path

# Allow running as a top-level script
sys.path.insert(0, str(Path(__file__).parent.parent))
from text2sql.config import GROQ_API_KEY, GROQ_MODEL, LLM_CALL_DELAY

if not GROQ_API_KEY:
    print("ERROR: GROQ_API_KEY is not set in .env")
    print("Copy .env.example to .env and add your key.")
    sys.exit(1)

print(f"Configured model : {GROQ_MODEL}")
print(f"API key present  : YES (not printed - SDD rule 9)\n")

# Import the Groq SDK.
try:
    from groq import Groq
except ImportError:
    print("ERROR: Groq SDK is not installed.")
    print("Run: pip install groq")
    sys.exit(1)

# (a) List available models
print("-- (a) Models available to your API key ----------------------")
client = Groq(api_key=GROQ_API_KEY, timeout=30.0, max_retries=0)

try:
    available_models = []
    for model in client.models.list():
        # Only show generative (text) models
        name = getattr(model, "id", str(model))
        available_models.append(name)
        print(f"  {name}")
except Exception as e:
    message = str(e).replace(GROQ_API_KEY, "[REDACTED]")
    print(f"ERROR listing models ({type(e).__name__}): {message}")
    sys.exit(1)

print(f"\nTotal models listed: {len(available_models)}\n")

# ── Check if configured model is in the list ───────────────────────────────
found = any(
    m == GROQ_MODEL
    for m in available_models
)

if not found:
    print(f"WARNING: Configured model '{GROQ_MODEL}' was NOT found in the list above.")
    print("Please check the model name in your .env file.")
    print("Update GROQ_MODEL and re-run this script.")
    sys.exit(1)

print(f"Configured model '{GROQ_MODEL}' is available. Proceeding with test call.\n")

# (b) One test call
print("-- (b) Test call ---------------------------------------------")
TEST_PROMPT = "Reply with exactly the words: LLM test call successful"

try:
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": TEST_PROMPT}],
        temperature=1,
        max_completion_tokens=2048,
        top_p=1,
        reasoning_effort="medium",
        stream=False,
    )
    # Sleep after the real call (SDD §8.7)
    time.sleep(LLM_CALL_DELAY)

    reply = response.choices[0].message.content or ""
    print(f"  Model response: {reply}")
    print("\nPhase 1 LLM check: PASS")

except Exception as e:
    message = str(e).replace(GROQ_API_KEY, "[REDACTED]")
    print(f"\nERROR making test call ({type(e).__name__}): {message}")
    print(
        "\nThe configured Groq model failed. See the model list above and update "
        "GROQ_MODEL in .env if needed."
    )
    sys.exit(1)
