"""
db/schema_utils.py — Read and format the database schema as text.

The schema text is included in every LLM prompt so the model knows
the table/column names and their types.

Format (SDD Section 9):
  One line per table: TableName(col TYPE, ...)
  One comment line per TEXT column with 8 or fewer distinct values,
  listing the possible values.
  A final relations line.
"""

import sqlite3
from text2sql.config import DB_PATH


def get_schema_text(db_path: str = DB_PATH, tables: list[str] | None = None) -> str:
    """
    Return the schema as a formatted string for use in LLM prompts.
    Supports pruning to a subset of tables.
    """
    conn = sqlite3.connect(db_path)
    cur  = conn.cursor()

    # Get list of all tables in creation order
    all_db_tables = [
        row[0]
        for row in cur.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid"
        ).fetchall()
    ]

    selected_tables = [t for t in all_db_tables if t in tables] if tables else all_db_tables

    lines = []
    for table in selected_tables:

        # Get column info: (cid, name, type, notnull, default, pk)
        cols = cur.execute(f"PRAGMA table_info({table})").fetchall()
        col_parts = [f"{col[1]} {col[2]}" for col in cols]
        lines.append(f"{table}({', '.join(col_parts)})")

        # For TEXT columns with 8 or fewer distinct values, list the values
        for col in cols:
            col_name = col[1]
            col_type = col[2].upper()
            if col_type == "TEXT":
                distinct = cur.execute(
                    f"SELECT DISTINCT {col_name} FROM {table} ORDER BY {col_name}"
                ).fetchall()
                if len(distinct) <= 8:
                    values = ", ".join(str(r[0]) for r in distinct if r[0] is not None)
                    lines.append(f"  -- {col_name} values: {values}")

    # Relations line (SDD §7.1)
    lines.append(
        "Relations: marks.student_id -> students.id; "
        "marks.course_id -> courses.course_id"
    )

    conn.close()
    return "\n".join(lines)


def get_all_tables(db_path: str = DB_PATH) -> list:
    """Return list of table names in the database."""
    conn = sqlite3.connect(db_path)
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY rowid"
        ).fetchall()
    ]
    conn.close()
    return tables


def get_columns(table: str, db_path: str = DB_PATH) -> list:
    """Return list of column names for a given table."""
    conn = sqlite3.connect(db_path)
    cols = [
        row[1]
        for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]
    conn.close()
    return cols


if __name__ == "__main__":
    print(get_schema_text())
