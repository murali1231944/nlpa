"""
executor.py — Safety Layer 2: Read-only SQLite query executor (SDD §8.9, §10).

Executes queries strictly through an enforced read-only SQLite connection URI
(mode=ro). Even if an unsafe query somehow bypassed Layer 1, SQLite refuses
any modification at the engine level.
"""

import sqlite3
from pathlib import Path
from text2sql.config import DB_PATH, MAX_ROWS


def run_query(sql: str, max_rows: int = MAX_ROWS) -> tuple[list[str], list[tuple]]:
    """
    Execute a SQL query against college.db using an enforced read-only connection.

    Args:
        sql: The SQL SELECT query to execute.
        max_rows: Maximum rows to return (default from config.MAX_ROWS).

    Returns:
        (column_names, rows)
        where column_names is list[str] and rows is list[tuple].

    Raises:
        sqlite3.Error: Propagated to caller for self-correction retry handling.
    """
    db_file = Path(DB_PATH).resolve()
    if not db_file.exists():
        raise FileNotFoundError(f"Database file not found: {db_file}")

    # Build read-only SQLite URI (SDD §8.9)
    uri = f"{db_file.as_uri()}?mode=ro"

    conn = sqlite3.connect(uri, uri=True)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description] if cursor.description else []
        rows = cursor.fetchmany(max_rows)
        return columns, rows
    finally:
        conn.close()
