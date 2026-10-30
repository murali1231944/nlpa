"""
tests/test_phase1.py — Acceptance tests for Phase 1 (SDD §15).

Run: pytest text2sql/tests/test_phase1.py -v
"""

import sqlite3
import json
import sys
from pathlib import Path
import pytest

# Make the text2sql package importable from the project root
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from text2sql.config import DB_PATH, EXAMPLES_PATH, TEST_Q_PATH
from text2sql.db.schema_utils import get_schema_text, get_all_tables, get_columns
from text2sql.data.loaders import load_examples, _check_example, load_test_questions


# ══════════════════════════════════════════════════════════════════════════════
#  DATABASE ACCEPTANCE CHECKS  (SDD §15 — "Database" row)
# ══════════════════════════════════════════════════════════════════════════════

class TestDatabase:
    """Verify the seed database matches the Section 15 acceptance criteria."""

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    def test_students_count(self):
        """60 students required (SDD §15)."""
        with self._conn() as conn:
            n = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
        assert n == 60, f"Expected 60 students, got {n}"

    def test_courses_count(self):
        """16 courses required (SDD §15)."""
        with self._conn() as conn:
            n = conn.execute("SELECT COUNT(*) FROM courses").fetchone()[0]
        assert n == 16, f"Expected 16 courses, got {n}"

    def test_marks_count(self):
        """240 marks rows required (SDD §15)."""
        with self._conn() as conn:
            n = conn.execute("SELECT COUNT(*) FROM marks").fetchone()[0]
        assert n == 240, f"Expected 240 marks rows, got {n}"

    def test_mangaluru_exists_in_city(self):
        """'Mangaluru' must exist in students.city (SDD §15)."""
        with self._conn() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM students WHERE city = 'Mangaluru'"
            ).fetchone()[0]
        assert n > 0, "Mangaluru not found in students.city"

    def test_dbms_exists_in_courses(self):
        """'DBMS' must exist in courses.course_name (SDD §15)."""
        with self._conn() as conn:
            n = conn.execute(
                "SELECT COUNT(*) FROM courses WHERE course_name = 'DBMS'"
            ).fetchone()[0]
        assert n > 0, "DBMS not found in courses.course_name"

    def test_foreign_keys_valid(self):
        """Every marks row must reference a valid student and course."""
        with self._conn() as conn:
            orphan_students = conn.execute(
                "SELECT COUNT(*) FROM marks m "
                "WHERE NOT EXISTS (SELECT 1 FROM students s WHERE s.id = m.student_id)"
            ).fetchone()[0]
            orphan_courses = conn.execute(
                "SELECT COUNT(*) FROM marks m "
                "WHERE NOT EXISTS (SELECT 1 FROM courses c WHERE c.course_id = m.course_id)"
            ).fetchone()[0]
        assert orphan_students == 0, f"{orphan_students} marks rows have invalid student_id"
        assert orphan_courses == 0, f"{orphan_courses} marks rows have invalid course_id"

    def test_schema_columns_students(self):
        """students table must have the columns from SDD §7.1."""
        cols = get_columns("students")
        expected = {"id", "name", "branch", "semester", "cgpa", "city"}
        assert expected.issubset(set(cols)), f"Missing columns: {expected - set(cols)}"

    def test_schema_columns_courses(self):
        """courses table must have the columns from SDD §7.1."""
        cols = get_columns("courses")
        expected = {"course_id", "course_name", "credits", "branch"}
        assert expected.issubset(set(cols)), f"Missing columns: {expected - set(cols)}"

    def test_schema_columns_marks(self):
        """marks table must have the columns from SDD §7.1."""
        cols = get_columns("marks")
        expected = {"student_id", "course_id", "marks", "attendance"}
        assert expected.issubset(set(cols)), f"Missing columns: {expected - set(cols)}"


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEMA UTILS
# ══════════════════════════════════════════════════════════════════════════════

class TestSchemaUtils:
    """Verify schema_utils produces sensible output."""

    def test_get_all_tables(self):
        """Should return the three tables in the DB."""
        tables = get_all_tables()
        assert "students" in tables
        assert "courses" in tables
        assert "marks" in tables

    def test_schema_text_contains_relations(self):
        """Schema text must include the relations line (SDD §9)."""
        text = get_schema_text()
        assert "Relations:" in text, "Schema text is missing the Relations line"

    def test_schema_text_lists_values(self):
        """Schema text must include possible values for TEXT columns with <= 8 distinct values."""
        text = get_schema_text()
        # branch has 5 values — must appear
        assert "CSE" in text, "CSE not found in schema text value listing"

    def test_schema_text_has_all_tables(self):
        """All three table definitions must appear in schema text."""
        text = get_schema_text()
        assert "students(" in text
        assert "courses(" in text
        assert "marks(" in text


# ══════════════════════════════════════════════════════════════════════════════
#  EXAMPLES LOADER
# ══════════════════════════════════════════════════════════════════════════════

class TestExamplesLoader:
    """Verify examples.json loads and validates correctly."""

    def test_loads_40_examples(self):
        """examples.json must contain exactly 40 items."""
        examples = load_examples()
        assert len(examples) == 40, f"Expected 40 examples, got {len(examples)}"

    def test_all_required_keys_present(self):
        """Every example must have id, question, sql, tags."""
        examples = load_examples()
        for ex in examples:
            for key in ("id", "question", "sql", "tags"):
                assert key in ex, f"Example id={ex.get('id')} missing key '{key}'"

    def test_ids_are_unique(self):
        """All example ids must be unique."""
        examples = load_examples()
        ids = [ex["id"] for ex in examples]
        assert len(ids) == len(set(ids)), "Duplicate ids in examples.json"

    def test_tags_are_valid(self):
        """Tags must only contain allowed values (SDD §7.3)."""
        valid = {"count", "filter", "aggregate", "group_by", "order_limit", "join"}
        examples = load_examples()
        for ex in examples:
            bad = set(ex["tags"]) - valid
            assert not bad, f"Example id={ex['id']} has invalid tags: {bad}"

    def test_sql_not_empty(self):
        """Every sql field must be a non-empty string."""
        examples = load_examples()
        for ex in examples:
            assert isinstance(ex["sql"], str) and ex["sql"].strip(), \
                f"Example id={ex['id']} has empty sql"


# ══════════════════════════════════════════════════════════════════════════════
#  TEST QUESTIONS LOADER  (format validator only — no content generated)
# ══════════════════════════════════════════════════════════════════════════════

class TestTestQuestionsLoader:
    """Verify the loader and format validator work correctly."""

    def test_loader_raises_if_file_missing(self, tmp_path):
        """If test_questions.json does not exist, FileNotFoundError is raised."""
        missing_path = str(tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError):
            load_test_questions(path=missing_path)

    def test_valid_item_passes(self, tmp_path):
        """A well-formed test question passes validation."""
        data = [
            {
                "id": 1,
                "level": "easy",
                "messy": False,
                "question": "How many students are there?",
                "gold_sql": "SELECT COUNT(*) FROM students;",
                "gold_tables": ["students"],
                "gold_columns": [],
                "gold_values": []
            }
        ]
        p = tmp_path / "tq.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_test_questions(path=str(p))
        assert len(result) == 1

    def test_invalid_level_rejected(self, tmp_path):
        """An invalid level value raises ValueError."""
        data = [
            {
                "id": 1,
                "level": "extreme",  # not valid
                "messy": False,
                "question": "?",
                "gold_sql": "SELECT 1;",
                "gold_tables": [],
                "gold_columns": [],
                "gold_values": []
            }
        ]
        p = tmp_path / "tq_bad.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="level"):
            load_test_questions(path=str(p))

    def test_gold_values_shape_validated(self, tmp_path):
        """gold_values entries must have 'column' and 'value' keys (CHANGELOG shape)."""
        data = [
            {
                "id": 1,
                "level": "easy",
                "messy": True,
                "question": "Students from Mangalore?",
                "gold_sql": "SELECT name FROM students WHERE city = 'Mangaluru';",
                "gold_tables": ["students"],
                "gold_columns": ["students.city"],
                "gold_values": [{"column": "students.city", "value": "Mangaluru"}]
            }
        ]
        p = tmp_path / "tq_ok.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        result = load_test_questions(path=str(p))
        assert result[0]["gold_values"][0]["column"] == "students.city"

    def test_gold_values_bad_shape_rejected(self, tmp_path):
        """gold_values with wrong shape raises ValueError."""
        data = [
            {
                "id": 1,
                "level": "easy",
                "messy": False,
                "question": "?",
                "gold_sql": "SELECT 1;",
                "gold_tables": [],
                "gold_columns": [],
                "gold_values": [{"wrong_key": "x"}]  # missing column/value
            }
        ]
        p = tmp_path / "tq_badgv.json"
        p.write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ValueError, match="column"):
            load_test_questions(path=str(p))
