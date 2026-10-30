"""
prompt_builder.py — Construct LLM prompts according to SDD §8.6 and §9.

Supports both:
  - Baseline mode: schema text + question only
  - Full mode: schema text + NLP hints + retrieved examples + question
  - Retry mode: includes previous failed SQL and sqlite error message
"""

from typing import Any


def _format_hints(hints: dict[str, Any]) -> str:
    """Format the NLP hints block according to SDD §9."""
    lines = ["Hints from NLP analysis (suggestions, verify against the question):"]

    # Aggregation
    agg = hints.get("aggregation") or hints.get("aggregates")
    if agg:
        if isinstance(agg, list):
            agg_str = ", ".join(str(a) for a in agg)
        else:
            agg_str = str(agg)
        lines.append(f"- Aggregation: {agg_str}")

    # Numeric conditions / top_n
    conds = hints.get("conditions") or hints.get("numeric_conditions")
    top_n = hints.get("top_n")
    cond_parts = []
    if conds:
        if isinstance(conds, list):
            for c in conds:
                if isinstance(c, dict):
                    cond_parts.append(f"{c.get('operator', '')} {c.get('value', '')}".strip())
                else:
                    cond_parts.append(str(c))
        else:
            cond_parts.append(str(conds))
    if top_n:
        cond_parts.append(f"LIMIT {top_n}")
    if cond_parts:
        lines.append(f"- Numeric conditions: {', '.join(cond_parts)}")

    # Likely columns (schema links)
    cols = hints.get("columns") or hints.get("likely_columns") or hints.get("schema_links")
    if cols:
        if isinstance(cols, list):
            col_names = []
            for c in cols:
                if isinstance(c, dict):
                    col_names.append(c.get("target", c.get("column", "")))
                elif isinstance(c, tuple):
                    col_names.append(c[0])
                else:
                    col_names.append(str(c))
            lines.append(f"- Likely columns: {', '.join(filter(None, col_names))}")
        else:
            lines.append(f"- Likely columns: {cols}")

    # Likely values (value links)
    vals = hints.get("values") or hints.get("likely_values") or hints.get("value_links")
    if vals:
        if isinstance(vals, list):
            for v in vals:
                if isinstance(v, dict):
                    lines.append(f"- Likely values: {v.get('column')} = '{v.get('value')}'")
                elif isinstance(v, tuple) and len(v) >= 2:
                    lines.append(f"- Likely values: {v[0]} = '{v[1]}'")
                else:
                    lines.append(f"- Likely values: {v}")
        else:
            lines.append(f"- Likely values: {vals}")

    # Only return if we actually added hints lines beyond the header
    if len(lines) > 1:
        return "\n".join(lines)
    return ""


def _format_examples(examples: list[dict[str, Any]]) -> str:
    """Format retrieved few-shot examples according to SDD §9."""
    if not examples:
        return ""
    lines = ["Similar solved examples:"]
    for ex in examples:
        q = ex.get("question", "").strip()
        sql = ex.get("sql", "").strip()
        lines.append(f"Question: {q}\nSQL: {sql}")
    return "\n\n".join(lines)


def build_prompt(
    question: str,
    schema_text: str,
    hints: dict[str, Any] | None = None,
    examples: list[dict[str, Any]] | None = None,
    error: str | None = None,
    previous_sql: str | None = None,
) -> str:
    """
    Build the complete Text-to-SQL prompt according to SDD §9.

    Args:
        question: User's natural language question.
        schema_text: Full or pruned database schema text.
        hints: Optional dictionary of extracted NLP hints. Omitted if empty.
        examples: Optional list of retrieved example dictionaries. Omitted if empty.
        error: SQLite error message (for retry calls only).
        previous_sql: The failed SQL string (for retry calls only).

    Returns:
        Structured prompt string ready for LLM generation.
    """
    sections = [
        "You are an expert SQLite query writer.\n"
        "Rules:\n"
        "- Output ONLY one SQL query. No explanation. No markdown.\n"
        "- Use only the tables and columns listed in the schema.\n"
        "- Only write SELECT queries.\n"
        "- Use JOINs and table aliases when more than one table is needed.\n"
        "- Use the exact stored values shown in the hints when filtering text columns.",
        f"Database schema:\n{schema_text.strip()}"
    ]

    # Hints section (omit if empty or None)
    if hints:
        formatted_hints = _format_hints(hints)
        if formatted_hints:
            sections.append(formatted_hints)

    # Examples section (omit if empty or None)
    if examples:
        formatted_examples = _format_examples(examples)
        if formatted_examples:
            sections.append(formatted_examples)

    # Retry section (only on retry when error and previous_sql are set)
    if error and previous_sql:
        sections.append(
            f"Your previous SQL was: {previous_sql.strip()}\n"
            f"It failed with this error: {error.strip()}\n"
            "Return only the corrected SQL."
        )

    # Final question and SQL trigger
    sections.append(f"Question: {question.strip()}\nSQL:")

    return "\n\n".join(sections)
