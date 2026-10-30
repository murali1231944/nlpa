"""
data/loaders.py — Load and validate examples.json and test_questions.json.

Both loaders raise clear errors on missing files or bad format so problems
are caught early, not silently ignored.
"""

import json
from pathlib import Path
from text2sql.config import EXAMPLES_PATH, TEST_Q_PATH

# ── Valid values for structured fields ─────────────────────────────────────
VALID_TAGS   = {"count", "filter", "aggregate", "group_by", "order_limit", "join"}
VALID_LEVELS = {"easy", "medium", "hard"}


# ══════════════════════════════════════════════════════════════════════════════
#  EXAMPLES LOADER  (data/examples.json)
# ══════════════════════════════════════════════════════════════════════════════

def load_examples(path: str = EXAMPLES_PATH) -> list:
    """
    Load the 40 solved examples used for prompt retrieval.

    Expected format (SDD §7.3):
        [
          {
            "id":       1,
            "question": "...",
            "sql":      "SELECT ...",
            "tags":     ["filter", "aggregate"]
          },
          ...
        ]

    Returns a list of dicts. Raises ValueError if format is wrong.
    """
    fpath = Path(path)
    if not fpath.exists():
        raise FileNotFoundError(
            f"examples.json not found at {path}. "
            "The human must supply this file (SDD §7.3)."
        )

    # utf-8-sig handles both plain UTF-8 and UTF-8-with-BOM files
    # (Windows tools like Notepad and PowerShell often write BOM)
    with open(fpath, encoding="utf-8-sig") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("examples.json must be a JSON array.")

    for i, item in enumerate(data):
        _check_example(item, i)

    return data


def _check_example(item: dict, index: int) -> None:
    """Validate a single example entry."""
    required = {"id", "question", "sql", "tags"}
    missing = required - item.keys()
    if missing:
        raise ValueError(
            f"examples.json item at index {index} is missing keys: {missing}"
        )
    if not isinstance(item["id"], int):
        raise ValueError(f"examples.json item {index}: 'id' must be an int.")
    if not isinstance(item["question"], str) or not item["question"].strip():
        raise ValueError(f"examples.json item {index}: 'question' must be a non-empty string.")
    if not isinstance(item["sql"], str) or not item["sql"].strip():
        raise ValueError(f"examples.json item {index}: 'sql' must be a non-empty string.")
    if not isinstance(item["tags"], list):
        raise ValueError(f"examples.json item {index}: 'tags' must be a list.")
    bad_tags = set(item["tags"]) - VALID_TAGS
    if bad_tags:
        raise ValueError(
            f"examples.json item {index}: unknown tags {bad_tags}. "
            f"Allowed: {VALID_TAGS}"
        )


# ══════════════════════════════════════════════════════════════════════════════
#  TEST QUESTIONS LOADER  (data/test_questions.json)
# ══════════════════════════════════════════════════════════════════════════════

def load_test_questions(path: str = TEST_Q_PATH) -> list:
    """
    Load the 15 human-authored test questions.

    The agent MUST NOT write, edit, or tune against this file (SDD §16 rule 2).
    This loader only reads and validates the format.

    Expected format (SDD §7.4, field shape clarified in CHANGELOG.md):
        [
          {
            "id":           1,
            "level":        "easy",
            "messy":        false,
            "question":     "...",
            "gold_sql":     "SELECT ...",
            "gold_tables":  ["students"],
            "gold_columns": ["students.name", "students.cgpa"],
            "gold_values":  [{"column": "students.city", "value": "Mangaluru"}]
          },
          ...
        ]

    Returns a list of dicts. Raises ValueError if format is wrong.
    """
    fpath = Path(path)
    if not fpath.exists():
        raise FileNotFoundError(
            f"test_questions.json not found at {path}. "
            "This file is authored by the human (SDD §7.4)."
        )

    # utf-8-sig handles both plain UTF-8 and UTF-8-with-BOM files
    with open(fpath, encoding="utf-8-sig") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("test_questions.json must be a JSON array.")

    for i, item in enumerate(data):
        _check_test_question(item, i)

    return data


def _check_test_question(item: dict, index: int) -> None:
    """Validate a single test question entry."""
    required = {
        "id", "level", "messy", "question",
        "gold_sql", "gold_tables", "gold_columns", "gold_values"
    }
    missing = required - item.keys()
    if missing:
        raise ValueError(
            f"test_questions.json item at index {index} is missing keys: {missing}"
        )

    if not isinstance(item["id"], int):
        raise ValueError(f"test_questions.json item {index}: 'id' must be int.")
    if item["level"] not in VALID_LEVELS:
        raise ValueError(
            f"test_questions.json item {index}: 'level' must be one of {VALID_LEVELS}."
        )
    if not isinstance(item["messy"], bool):
        raise ValueError(f"test_questions.json item {index}: 'messy' must be bool.")
    if not isinstance(item["question"], str) or not item["question"].strip():
        raise ValueError(f"test_questions.json item {index}: 'question' must be non-empty string.")
    if not isinstance(item["gold_sql"], str) or not item["gold_sql"].strip():
        raise ValueError(f"test_questions.json item {index}: 'gold_sql' must be non-empty string.")
    if not isinstance(item["gold_tables"], list):
        raise ValueError(f"test_questions.json item {index}: 'gold_tables' must be a list.")
    if not isinstance(item["gold_columns"], list):
        raise ValueError(f"test_questions.json item {index}: 'gold_columns' must be a list.")
    if not isinstance(item["gold_values"], list):
        raise ValueError(f"test_questions.json item {index}: 'gold_values' must be a list.")
    # Validate each gold_value object has 'column' and 'value' keys
    # (shape chosen in CHANGELOG.md: {"column": "table.col", "value": "stored_value"})
    for j, gv in enumerate(item["gold_values"]):
        if not isinstance(gv, dict) or "column" not in gv or "value" not in gv:
            raise ValueError(
                f"test_questions.json item {index}, gold_values[{j}]: "
                "each entry must be a dict with 'column' and 'value' keys."
            )


# ══════════════════════════════════════════════════════════════════════════════
#  Quick self-test (run: python text2sql/data/loaders.py)
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    print("── examples.json ──────────────────────────────────────────")
    try:
        ex = load_examples()
        print(f"  Loaded {len(ex)} examples. First item id={ex[0]['id']}")
    except FileNotFoundError as e:
        print(f"  NOT FOUND (expected — human must supply): {e}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n── test_questions.json ────────────────────────────────────")
    try:
        tq = load_test_questions()
        print(f"  Loaded {len(tq)} test questions. First id={tq[0]['id']}")
    except FileNotFoundError as e:
        print(f"  NOT FOUND (expected — human must supply): {e}")
    except Exception as e:
        print(f"  ERROR: {e}")
