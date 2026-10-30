"""
test_phase2.py — Test suite for Phase 2: Baseline Pipeline & Safety Layers.

Verifies:
  - Safety Layer 1 (validator.py): blocks destructive/multi-statement queries, allows safe SELECTs
  - Safety Layer 2 (executor.py): read-only connection enforces no-writes at SQLite level
  - Prompt builder (prompt_builder.py): baseline layout, hints omission, retry section
  - Client SQL cleaner (client.py): markdown stripping, label removal, semicolon normalization
  - Pipeline (pipeline.py): baseline execution, retry on SQLite error, no retry on 0-row results, blocked query handling
"""

import sqlite3
import pytest
from text2sql.core.validator import is_safe
from text2sql.core.executor import run_query
from text2sql.llm.prompt_builder import build_prompt
from text2sql.llm.client import clean_sql
from text2sql.core.pipeline import answer
from text2sql.db.schema_utils import get_schema_text


# ═══════════════════════════════════════════════════════════════════════════
# 1. Safety Layer 1: Validator Acceptance Checks (SDD §8.8, §15)
# ═══════════════════════════════════════════════════════════════════════════

class TestValidator:
    """Acceptance checks from SDD §15 for validator.py."""

    def test_blocks_drop_table(self):
        # SDD §15: blocked: DROP TABLE students;
        safe, reason = is_safe("DROP TABLE students;")
        assert not safe
        assert "DROP" in reason.upper() or "SELECT" in reason.upper()

    def test_blocks_multi_statement_delete(self):
        # SDD §15: blocked: SELECT * FROM students; DELETE FROM students;
        safe, reason = is_safe("SELECT * FROM students; DELETE FROM students;")
        assert not safe
        assert "MULTIPLE" in reason.upper() or "SEMICOLON" in reason.upper() or "DELETE" in reason.upper()

    def test_blocks_update_statement(self):
        # SDD §15: blocked: UPDATE students SET cgpa = 10;
        safe, reason = is_safe("UPDATE students SET cgpa = 10;")
        assert not safe
        assert "UPDATE" in reason.upper() or "SELECT" in reason.upper()

    def test_blocks_insert_and_alter(self):
        safe, _ = is_safe("INSERT INTO students VALUES (1, 'Test', 'CSE', 'Pune', 9.0);")
        assert not safe

        safe, _ = is_safe("ALTER TABLE students ADD COLUMN test INT;")
        assert not safe

    def test_blocks_pragma_and_attach(self):
        safe, _ = is_safe("PRAGMA table_info(students);")
        assert not safe

        safe, _ = is_safe("ATTACH DATABASE 'malicious.db' AS evil;")
        assert not safe

    def test_allows_normal_select(self):
        # SDD §15: allowed: SELECT name FROM students WHERE cgpa > 9;
        safe, reason = is_safe("SELECT name FROM students WHERE cgpa > 9;")
        assert safe
        assert reason == ""

    def test_allows_literal_containing_update(self):
        # SDD §15: allowed: a SELECT whose string literal contains the word update
        query = "SELECT * FROM courses WHERE course_name = 'Software Updates';"
        safe, reason = is_safe(query)
        assert safe
        assert reason == ""

    def test_allows_literal_containing_delete(self):
        query = "SELECT * FROM students WHERE name = 'Deleted User';"
        safe, reason = is_safe(query)
        assert safe

    def test_strips_comments_and_allows_safe_query(self):
        query = "/* comment with word drop */ SELECT name FROM students;"
        safe, reason = is_safe(query)
        assert safe

    def test_rejects_empty_query(self):
        safe, reason = is_safe("")
        assert not safe

        safe, reason = is_safe("   -- only comment\n  ")
        assert not safe


# ═══════════════════════════════════════════════════════════════════════════
# 2. Safety Layer 2: Executor Acceptance Checks (SDD §8.9, §15)
# ═══════════════════════════════════════════════════════════════════════════

class TestExecutor:
    """Acceptance checks from SDD §15 for executor.py."""

    def test_normal_select_runs(self):
        # SDD §15: a normal SELECT runs
        cols, rows = run_query("SELECT name, city FROM students LIMIT 5;")
        assert cols == ["name", "city"]
        assert len(rows) == 5

    def test_attempted_write_raises_error(self):
        # SDD §15: an attempted write on the read-only connection raises an error
        with pytest.raises(sqlite3.Error):
            run_query("UPDATE students SET cgpa = 10;")

    def test_respects_max_rows(self):
        cols, rows = run_query("SELECT id FROM students;", max_rows=10)
        assert len(rows) == 10

    def test_sqlite_error_propagates(self):
        with pytest.raises(sqlite3.Error):
            run_query("SELECT nonexistent_col FROM students;")


# ═══════════════════════════════════════════════════════════════════════════
# 3. Prompt Builder (SDD §8.6, §9)
# ═══════════════════════════════════════════════════════════════════════════

class TestPromptBuilder:
    def test_baseline_prompt_structure(self):
        schema = get_schema_text()
        prompt = build_prompt("Show all students", schema_text=schema)

        # Must contain standard instructions and rules
        assert "You are an expert SQLite query writer." in prompt
        assert "Rules:" in prompt
        assert "Database schema:" in prompt
        assert "Question: Show all students" in prompt
        assert prompt.endswith("SQL:")

        # Must NOT contain hints or examples in baseline mode
        assert "Hints from NLP analysis" not in prompt
        assert "Similar solved examples:" not in prompt
        assert "Your previous SQL was:" not in prompt

    def test_retry_prompt_structure(self):
        schema = get_schema_text()
        prompt = build_prompt(
            question="Show all students",
            schema_text=schema,
            error="no such column: fake_col",
            previous_sql="SELECT fake_col FROM students;",
        )

        assert "Your previous SQL was: SELECT fake_col FROM students;" in prompt
        assert "It failed with this error: no such column: fake_col" in prompt
        assert "Return only the corrected SQL." in prompt


# ═══════════════════════════════════════════════════════════════════════════
# 4. Client Output Sanitization (SDD §8.7)
# ═══════════════════════════════════════════════════════════════════════════

class TestClientSanitizer:
    def test_clean_sql_fences(self):
        raw = "```sql\nSELECT name FROM students;\n```"
        assert clean_sql(raw) == "SELECT name FROM students;"

    def test_clean_sql_label(self):
        raw = "SQL: SELECT name FROM students;"
        assert clean_sql(raw) == "SELECT name FROM students;"

    def test_clean_sql_semicolon_added(self):
        raw = "SELECT name FROM students"
        assert clean_sql(raw) == "SELECT name FROM students;"

    def test_clean_sql_first_statement_only(self):
        raw = "SELECT name FROM students; SELECT city FROM students;"
        assert clean_sql(raw) == "SELECT name FROM students;"


# ═══════════════════════════════════════════════════════════════════════════
# 5. Baseline Pipeline & Retry Logic (SDD §8.10, §15)
# ═══════════════════════════════════════════════════════════════════════════

class TestPipeline:
    def test_baseline_successful_query(self):
        dummy_llm = lambda p: "SELECT name, branch FROM students WHERE city = 'Mangaluru';"
        result = answer("Students from Mangaluru", mode="baseline", custom_llm_fn=dummy_llm)

        assert result["error"] is None
        assert result["columns"] == ["name", "branch"]
        assert len(result["rows"]) > 0
        assert result["retried"] is False
        assert result["llm_calls"] == 1
        assert "timings" in result
        assert "nlp" in result

    def test_zero_row_triggers_zero_retries(self):
        # SDD §15: a zero-row result triggers none
        dummy_llm = lambda p: "SELECT name FROM students WHERE cgpa > 100;"
        result = answer("Students with impossible cgpa", mode="baseline", custom_llm_fn=dummy_llm)

        assert result["error"] is None
        assert result["rows"] == []
        assert result["retried"] is False
        assert result["llm_calls"] == 1

    def test_broken_query_triggers_exactly_one_retry(self):
        # SDD §15: a deliberately broken query triggers exactly one retry
        call_count = 0

        def failing_then_fixed_llm(p):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return "SELECT non_existent_col FROM students;"
            else:
                return "SELECT id FROM students LIMIT 3;"

        result = answer("Test retry", mode="baseline", custom_llm_fn=failing_then_fixed_llm)

        assert result["retried"] is True
        assert result["llm_calls"] == 2
        assert call_count == 2
        assert result["error"] is None
        assert len(result["rows"]) == 3

    def test_blocked_query_triggers_zero_retries_and_does_not_execute(self):
        # SDD §8.10: Never retry a blocked query. DO NOT execute.
        dummy_llm = lambda p: "DROP TABLE students;"
        result = answer("Delete table", mode="baseline", custom_llm_fn=dummy_llm)

        assert result["retried"] is False
        assert result["llm_calls"] == 1
        assert "Blocked by safety validator" in result["error"]
        assert result["columns"] == []
        assert result["rows"] == []
