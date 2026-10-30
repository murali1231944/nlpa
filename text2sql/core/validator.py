"""
validator.py — Safety Layer 1: Regex-based SQL validator (SDD §8.8, §10).

Ensures only single, read-only SELECT queries are executed.
Destructive commands, data modification statements, multi-statement injection,
and administrative PRAGMA statements are blocked before touching SQLite.
"""

import re

# Disallowed SQL keywords per SDD §8.8
DISALLOWED_KEYWORDS = {
    "drop", "delete", "update", "insert", "alter", "create",
    "replace", "attach", "detach", "pragma", "truncate", "vacuum", "reindex"
}

_KEYWORD_PATTERN = re.compile(
    r"\b(" + "|".join(DISALLOWED_KEYWORDS) + r")\b",
    re.IGNORECASE
)


def _strip_comments(sql: str) -> str:
    """Remove multi-line (/* ... */) and single-line (-- ...) SQL comments."""
    # Multi-line comments
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    # Single-line comments
    sql = re.sub(r"--[^\r\n]*", " ", sql)
    return sql


def _blank_string_literals(sql: str) -> str:
    """
    Replace the contents of string literals with empty quotes.
    Handles escaped quotes ('' inside single quotes).
    Prevents false alarms when literals contain words like 'update' or 'delete'.
    """
    # Replace single-quoted string literals: '...'
    sql = re.sub(r"'(?:''|[^'])*'", "''", sql)
    # Also handle double-quoted identifiers / strings: "..."
    sql = re.sub(r'"(?:""|[^"])*"', '""', sql)
    return sql


def is_safe(sql: str) -> tuple[bool, str]:
    """
    Validate whether a SQL statement is safe to execute.

    Rules enforced (SDD §8.8):
      1. Strip SQL comments.
      2. Blank out contents of string literals (prevents false positive on words like 'update').
      3. Require text to start with SELECT.
      4. Require exactly one statement (no semicolon except an optional final one).
      5. Reject whole-word occurrence of disallowed keywords (DROP, DELETE, UPDATE, INSERT, etc.).

    Returns:
      (True, "") if safe.
      (False, reason) if blocked.
    """
    if not sql or not sql.strip():
        return False, "Query is empty"

    # Step 1: Strip SQL comments
    cleaned = _strip_comments(sql)

    # Step 2: Blank out string literals
    cleaned = _blank_string_literals(cleaned).strip()

    if not cleaned:
        return False, "Query contains only comments or empty string"

    # Step 3: Require exactly one statement (check semicolons)
    # Strip optional trailing semicolon
    stmt_body = cleaned
    if stmt_body.endswith(";"):
        stmt_body = stmt_body[:-1].strip()

    if ";" in stmt_body:
        return False, "Multiple SQL statements detected (semicolon inside query)"

    # Step 4: Require text to start with SELECT
    # Handles optional leading parentheses or whitespace, e.g. (SELECT ...) or SELECT ...
    normalized = stmt_body.lower()
    if not re.match(r"^\s*\(?\s*select\b", normalized):
        return False, "Query must start with SELECT"

    # Step 5: Reject whole-word occurrences of disallowed keywords
    match = _KEYWORD_PATTERN.search(normalized)
    if match:
        blocked_word = match.group(1).upper()
        return False, f"Disallowed keyword detected: {blocked_word}"

    return True, ""
