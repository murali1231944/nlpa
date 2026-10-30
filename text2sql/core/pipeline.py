"""
pipeline.py — End-to-end Text-to-SQL pipeline (SDD §8.10).

Orchestrates:
  1. NLP stage (full mode) or Schema lookup (baseline mode)
  2. Prompt building
  3. LLM generation (via client with disk cache)
  4. Layer 1 Safety validation
  5. Layer 2 Read-only execution with single retry on SQLite execution error
"""

import sqlite3
import time
from typing import Any

from text2sql.config import MAX_RETRIES, MAX_ROWS
from text2sql.core.executor import run_query
from text2sql.core.validator import is_safe
from text2sql.db.schema_utils import get_schema_text
from text2sql.llm.client import generate_sql
from text2sql.llm.prompt_builder import build_prompt


def answer(
    question: str,
    mode: str = "baseline",
    bypass_cache: bool = False,
    custom_llm_fn=None,
) -> dict[str, Any]:
    """
    Run the Text-to-SQL pipeline on a natural language question.

    Args:
        question: User query string.
        mode: "baseline" or "full".
        bypass_cache: If True, bypass LLM disk cache.
        custom_llm_fn: Optional callable for testing (prompt: str) -> str.

    Returns:
        dict containing:
          question, mode, nlp, prompt, sql, columns, rows, error,
          retried, llm_calls, timings
    """
    llm_generate = custom_llm_fn if custom_llm_fn is not None else (
        lambda p: generate_sql(p, bypass_cache=bypass_cache)
    )

    t0_nlp = time.perf_counter()

    nlp_payload: dict[str, Any] = {
        "analysis": None,
        "hints": None,
        "schema_links": [],
        "value_links": [],
        "retrieved_examples": [],
        "pruned_tables": [],
    }

    schema_text = get_schema_text()
    hints = None
    examples = None

    if mode == "full":
        # Phase 3 hooks: will be wired in Phase 3
        try:
            from text2sql.nlp.pipeline_nlp import run_nlp_stages
            nlp_result = run_nlp_stages(question)
            nlp_payload = nlp_result["nlp"]
            hints = nlp_result.get("hints")
            examples = nlp_result.get("examples")
            schema_text = nlp_result.get("schema_text", schema_text)
        except ImportError:
            # Full mode requested before Phase 3 modules installed
            pass

    t1_nlp = time.perf_counter()
    nlp_ms = (t1_nlp - t0_nlp) * 1000.0

    # ── Step 2: Build prompt and generate SQL ──────────────────────────────
    t0_llm = time.perf_counter()
    current_prompt = build_prompt(
        question=question,
        schema_text=schema_text,
        hints=hints,
        examples=examples,
    )

    llm_calls = 1
    retried = False
    error_msg = None
    columns: list[str] = []
    rows: list[tuple] = []

    sql = llm_generate(current_prompt)

    # ── Step 3: Layer 1 Safety Validation ──────────────────────────────────
    safe, reason = is_safe(sql)
    if not safe:
        t1_llm = time.perf_counter()
        return {
            "question": question,
            "mode": mode,
            "nlp": nlp_payload,
            "prompt": current_prompt,
            "sql": sql,
            "columns": [],
            "rows": [],
            "error": f"Blocked by safety validator: {reason}",
            "retried": False,
            "llm_calls": llm_calls,
            "timings": {
                "nlp_ms": round(nlp_ms, 2),
                "llm_ms": round((t1_llm - t0_llm) * 1000.0, 2),
            },
        }

    # ── Step 4: Layer 2 Execution & Retry on SQLite Error ──────────────────
    try:
        columns, rows = run_query(sql, max_rows=MAX_ROWS)
    except sqlite3.Error as initial_err:
        # Check if retries remain (SDD §8.10: MAX_RETRIES)
        if MAX_RETRIES > 0:
            retried = True
            llm_calls += 1

            # Build retry prompt with failed SQL and error
            retry_prompt = build_prompt(
                question=question,
                schema_text=schema_text,
                hints=hints,
                examples=examples,
                error=str(initial_err),
                previous_sql=sql,
            )
            current_prompt = retry_prompt

            try:
                retry_sql = llm_generate(retry_prompt)
                sql = retry_sql

                safe_retry, reason_retry = is_safe(sql)
                if not safe_retry:
                    error_msg = f"Blocked by safety validator on retry: {reason_retry}"
                else:
                    columns, rows = run_query(sql, max_rows=MAX_ROWS)
                    error_msg = None
            except sqlite3.Error as retry_err:
                error_msg = f"SQLite error after retry: {retry_err}"
            except Exception as e:
                error_msg = f"Error during retry: {e}"
        else:
            error_msg = f"SQLite error: {initial_err}"

    t1_llm = time.perf_counter()
    llm_ms = (t1_llm - t0_llm) * 1000.0

    return {
        "question": question,
        "mode": mode,
        "nlp": nlp_payload,
        "prompt": current_prompt,
        "sql": sql,
        "columns": columns,
        "rows": rows,
        "error": error_msg,
        "retried": retried,
        "llm_calls": llm_calls,
        "timings": {
            "nlp_ms": round(nlp_ms, 2),
            "llm_ms": round(llm_ms, 2),
        },
    }


if __name__ == "__main__":
    import sys

    q = sys.argv[1] if len(sys.argv) > 1 else "Show 5 students from Mangaluru"
    m = sys.argv[2] if len(sys.argv) > 2 else "baseline"

    print(f"Question : {q}")
    print(f"Mode     : {m}")
    print("-" * 50)

    try:
        res = answer(q, mode=m)
        print(f"Generated SQL : {res['sql']}")
        if res["error"]:
            print(f"Error         : {res['error']}")
        else:
            print(f"Columns       : {res['columns']}")
            print(f"Rows ({len(res['rows'])} returned):")
            for r in res["rows"][:10]:
                print(f"  {r}")
        print(f"Retried       : {res['retried']}")
        print(f"LLM Calls     : {res['llm_calls']}")
        print(f"Timings (ms)  : {res['timings']}")
    except Exception as e:
        print(f"Execution Error: {e}")

