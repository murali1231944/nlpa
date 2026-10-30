"""
value_linking.py — Fuzzy matching for cell values using RapidFuzz (SDD §8.4, §15).

Demonstrates:
  - n-gram generation (n = 1 to 3)
  - String normalization and stop-word / schema-word filtering
  - Levenshtein / edit distance via RapidFuzz fuzz.ratio
  - Exact matching guard for short acronyms (e.g. 'CSE')
  - City name variant / alias handling (e.g. Mangalore -> Mangaluru)
  - Overlap resolution (longest span wins)
"""

import sqlite3
from typing import Any
from rapidfuzz import fuzz

from text2sql.config import DB_PATH, MIN_FUZZY_LEN, VALUE_LINK_THRESHOLD

# Schema words and common stop words that must NEVER produce a value link (SDD §8.4, §15)
STOP_WORDS = {
    "a", "an", "the", "in", "on", "at", "from", "with", "by", "for", "to", "of",
    "is", "are", "was", "were", "be", "been", "have", "has", "had", "and", "or",
    "not", "show", "find", "list", "get", "give", "who", "what", "which", "where",
    "how", "many", "than", "above", "below", "between", "over", "under", "all",
    "any", "some", "top", "first", "last", "per"
}

SCHEMA_WORDS = {
    "student", "students", "pupil", "pupils", "course", "courses", "subject", "subjects",
    "mark", "marks", "grade", "grades", "score", "scores", "attendance", "cgpa", "gpa",
    "city", "branch", "credit", "credits", "semester", "sem", "average", "avg",
    "count", "sum", "min", "max", "total", "table", "select", "where", "percent", "%"
}

# Hand-written synonym list for historical / colonial city names
# Target values MUST exist in college.db (students.city)
CITY_ALIASES = {
    "mangalore": "Mangaluru",
    "bangalore": "Bengaluru",
    "mysore": "Mysuru",
    "hubli": "Hubballi",
}


def _load_categorical_values(db_path: str = DB_PATH) -> tuple[dict[str, list[str]], dict[str, str]]:
    """
    Load distinct values for categorical columns from the database (SDD §8.4).
    Also validates that every alias in CITY_ALIASES exists in college.db.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    db_cities = set(r[0] for r in cur.execute("SELECT DISTINCT city FROM students WHERE city IS NOT NULL").fetchall())

    # Check and filter alias targets: keep only those whose target value exists in college.db
    valid_aliases = {}
    for alias_src, target_val in CITY_ALIASES.items():
        if target_val in db_cities:
            valid_aliases[alias_src] = target_val
        else:
            print(f"WARNING: Alias target '{target_val}' not found in students.city; pruned.")

    values = {
        "students.branch": [r[0] for r in cur.execute("SELECT DISTINCT branch FROM students WHERE branch IS NOT NULL").fetchall()],
        "students.city": sorted(list(db_cities)),
        "courses.course_name": [r[0] for r in cur.execute("SELECT DISTINCT course_name FROM courses WHERE course_name IS NOT NULL").fetchall()],
    }
    conn.close()
    return values, valid_aliases


# Cache values and validated aliases at module import
_CAT_VALUES = None
_VALID_ALIASES = None


def get_categorical_values() -> tuple[dict[str, list[str]], dict[str, str]]:
    """Lazily load and cache database values and validated aliases."""
    global _CAT_VALUES, _VALID_ALIASES
    if _CAT_VALUES is None or _VALID_ALIASES is None:
        _CAT_VALUES, _VALID_ALIASES = _load_categorical_values()
    return _CAT_VALUES, _VALID_ALIASES



def _build_ngrams(tokens: list[str]) -> list[tuple[str, int, int]]:
    """
    Generate 1-grams, 2-grams, and 3-grams with their token span (start, end).
    """
    ngrams = []
    clean_tokens = [t.strip().lower() for t in tokens if t.strip()]
    n_tokens = len(clean_tokens)

    for n in (3, 2, 1):  # Longer n-grams first
        for i in range(n_tokens - n + 1):
            span_tokens = clean_tokens[i:i + n]
            phrase = " ".join(span_tokens)
            ngrams.append((phrase, i, i + n))
    return ngrams


def _is_skippable(phrase: str) -> bool:
    """Check if an n-gram consists only of stop words, schema words, or numbers."""
    parts = phrase.split()
    if not parts:
        return True
    # Pure numeric
    if all(p.replace(".", "").isdigit() for p in parts):
        return True
    # All stop words or schema words
    if all(p in STOP_WORDS or p in SCHEMA_WORDS for p in parts):
        return True
    return False


def link_values(
    tokens: list[str],
    threshold: int = VALUE_LINK_THRESHOLD,
    use_alias_map: bool = True,
) -> list[dict[str, Any]]:
    """
    Fuzzy-match question tokens against distinct database cell values (SDD §8.4).

    Rules:
      1. Build 1- to 3-grams from tokens.
      2. Skip n-grams that are all stop words, numbers, or schema words ('average', 'marks', etc.).
      3. For n-grams < MIN_FUZZY_LEN characters: require exact case-insensitive match (e.g. 'cse' -> 'CSE').
      4. Otherwise compare with RapidFuzz fuzz.ratio, case-insensitive, accepting score >= threshold.
      5. Alias mapping converts colonial city names (e.g. Mangalore -> Mangaluru).
      6. When spans overlap, keep the longer span.

    Returns:
      list of dicts: [{'phrase': str, 'column': str, 'value': str, 'score': float}]
    """
    cat_values, valid_aliases = get_categorical_values()
    ngrams = _build_ngrams(tokens)

    candidates = []

    for phrase, start_idx, end_idx in ngrams:
        if _is_skippable(phrase):
            continue

        # Check validated alias map first
        alias_target = valid_aliases.get(phrase) if use_alias_map else None

        best_match = None
        best_score = 0.0
        best_col = None

        for col, stored_vals in cat_values.items():
            for stored_val in stored_vals:
                stored_lower = stored_val.lower()

                # If alias matched exactly to this stored value:
                if alias_target and alias_target.lower() == stored_lower:
                    best_match = stored_val
                    best_col = col
                    best_score = 100.0
                    break

                # Rule 3: Short tokens (< MIN_FUZZY_LEN) require exact case-insensitive match
                if len(phrase) < MIN_FUZZY_LEN:
                    if phrase == stored_lower:
                        best_match = stored_val
                        best_col = col
                        best_score = 100.0
                        break
                else:
                    # Rule 4: RapidFuzz fuzz.ratio
                    score = float(fuzz.ratio(phrase, stored_lower))
                    if score >= threshold and score > best_score:
                        best_score = score
                        best_match = stored_val
                        best_col = col

            if best_score == 100.0:
                break

        if best_match and best_score >= threshold:
            candidates.append({
                "phrase": phrase,
                "column": best_col,
                "value": best_match,
                "score": round(best_score, 1),
                "span": (start_idx, end_idx),
                "span_length": end_idx - start_idx,
            })

    # Rule 5: Overlap resolution — sort by span_length (descending) and keep longest non-overlapping
    candidates.sort(key=lambda c: (c["span_length"], c["score"]), reverse=True)
    selected = []
    occupied_indices = set()

    for cand in candidates:
        span_range = set(range(cand["span"][0], cand["span"][1]))
        if not (span_range & occupied_indices):
            occupied_indices.update(span_range)
            selected.append({
                "phrase": cand["phrase"],
                "column": cand["column"],
                "value": cand["value"],
                "score": cand["score"],
            })

    return selected
