"""
extraction.py — Rule-based extraction of SQL hints from questions (SDD §8.2, §15).

Demonstrates:
  - Pattern matching with regular expressions
  - Keyword lookup for SQL aggregate functions
  - Comparison operator mapping
  - Numeric operand extraction and top-N clause detection
"""

import re
from typing import Any

# Aggregates mapping (SDD §8.2)
# Checked in order of specificity
AGGREGATE_PATTERNS = [
    (re.compile(r"\b(how many|number of|total number|count)\b", re.IGNORECASE), "COUNT"),
    (re.compile(r"\b(average|avg|mean)\b", re.IGNORECASE), "AVG"),
    (re.compile(r"\b(sum|total)\b", re.IGNORECASE), "SUM"),
    (re.compile(r"\b(highest|maximum|max|best)\b", re.IGNORECASE), "MAX"),
    (re.compile(r"\b(lowest|minimum|min|worst)\b", re.IGNORECASE), "MIN"),
]

# Comparison operators mapping (SDD §8.2)
# Multi-word patterns must be checked BEFORE single-word patterns
# (e.g., 'at least' must match '>=' before 'least' or other tokens)
OPERATOR_PATTERNS = [
    (r"\b(at least|no less than|greater than or equal to|minimum of)\b", ">="),
    (r"\b(at most|no more than|less than or equal to|maximum of)\b", "<="),
    (r"\b(above|greater than|more than|exceeding|higher than|over)\b", ">"),
    (r"\b(below|less than|under|lower than|fewer than)\b", "<"),
    (r"\b(equal to|equals|is exactly)\b", "="),
    (r"\b(not equal to|different from|not)\b", "!="),
]


def _extract_aggregates(text: str) -> list[str]:
    """Find SQL aggregate functions indicated by keywords in the text."""
    aggs = []
    # Avoid counting 'total number' as SUM
    if re.search(r"\btotal\s+number\b", text, re.IGNORECASE):
        aggs.append("COUNT")
        text = re.sub(r"\btotal\s+number\b", "", text, flags=re.IGNORECASE)

    for pattern, agg_name in AGGREGATE_PATTERNS:
        if pattern.search(text) and agg_name not in aggs:
            aggs.append(agg_name)
    return aggs


def _extract_top_n(text: str) -> int | None:
    """Extract top-N limit if present, e.g., 'top 5 students' -> 5."""
    match = re.search(r"\b(?:top|first)\s+(\d+)\b", text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def _extract_conditions(text: str) -> list[dict[str, Any]]:
    """
    Extract comparison operators and their numeric operands.
    Examples:
      'attendance above 75%' -> [{'operator': '>', 'value': 75.0}]
      'at least 5 marks'     -> [{'operator': '>=', 'value': 5.0}]
    """
    conditions = []

    # Combined regex: <operator phrase> [optional filler words] <number> [%]?
    for op_phrase_regex, symbol in OPERATOR_PATTERNS:
        pattern = rf"{op_phrase_regex}\s*(?:of\s+)?(?:marks\s+|attendance\s+|cgpa\s+|credits\s+)?(\d+(?:\.\d+)?)\s*%?"
        for m in re.finditer(pattern, text, re.IGNORECASE):
            val_str = m.group(2)  # Group 1 is the operator phrase, Group 2 is the number
            try:
                val = float(val_str)
                # Keep as int if whole number
                val_formatted = int(val) if val.is_integer() else val
                conditions.append({
                    "operator": symbol,
                    "value": val_formatted,
                    "raw_phrase": m.group(0).strip(),
                })
            except ValueError:
                continue

    return conditions


def extract_hints(analysis: dict[str, Any] | None, question: str) -> dict[str, Any]:
    """
    Extract hints (aggregates, conditions, top_n) from the question and spaCy analysis.

    Args:
        analysis: Dictionary from preprocess.analyse() containing tokens, lemmas, etc.
        question: Original natural language question string.

    Returns:
        dict with keys:
          'aggregates': list[str] (e.g. ['AVG'])
          'conditions': list[dict] (e.g. [{'operator': '>', 'value': 75}])
          'top_n': int | None (e.g. 5)
    """
    text = question.strip()

    aggregates = _extract_aggregates(text)
    top_n = _extract_top_n(text)
    conditions = _extract_conditions(text)

    return {
        "aggregates": aggregates,
        "conditions": conditions,
        "top_n": top_n,
    }
