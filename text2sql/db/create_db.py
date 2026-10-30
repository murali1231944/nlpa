"""
create_db.py — Database creation and seed data script (SDD §7.1, §7.2, §15).

Schema:
  students(id INTEGER PRIMARY KEY, name TEXT, branch TEXT, semester INTEGER, cgpa REAL, city TEXT)
  courses(course_id INTEGER PRIMARY KEY, course_name TEXT, credits INTEGER, branch TEXT)
  marks(student_id INTEGER, course_id INTEGER, marks INTEGER, attendance INTEGER)

Seed data per SDD §7.2:
  - 60 students: ids 1 to 60, branch in (CSE, ISE, ECE, MECH), semester in (3, 5, 7),
    cgpa in 6.00 to 9.80, city in (Bengaluru, Mysuru, Mangaluru, Hubballi, Chennai, Hyderabad).
  - 16 courses: 4 per branch, credits 3 or 4.
  - 240 marks rows: every student gets a row for each of the 4 courses of their own branch.
    marks 30 to 100, attendance 55 to 100.
  - Guaranteed exact spellings: Mangaluru, DBMS.
"""

import random
import sqlite3
from pathlib import Path
from text2sql.config import DB_PATH

# Seed for reproducibility — same DB every run (SDD §7.2)
random.seed(42)

BRANCHES = ["CSE", "ISE", "ECE", "MECH"]
SEMESTERS = [3, 5, 7]
CITIES = ["Bengaluru", "Mysuru", "Mangaluru", "Hubballi", "Chennai", "Hyderabad"]

FIRST_NAMES = [
    "Ravi", "Priya", "Arjun", "Ananya", "Karthik", "Sneha", "Rahul",
    "Divya", "Vikram", "Meera", "Suresh", "Pooja", "Aditya", "Kavya", "Manoj"
]
SURNAMES = ["Sharma", "Rao", "Gowda", "Nair", "Reddy", "Iyer", "Patil", "Shetty"]

# 16 courses — 4 per branch, credits 3 or 4 (SDD §7.2)
COURSES = [
    # CSE
    ("DBMS", 4, "CSE"),
    ("Algorithms", 4, "CSE"),
    ("Operating Systems", 3, "CSE"),
    ("NLP", 3, "CSE"),
    # ISE
    ("Data Mining", 4, "ISE"),
    ("Computer Networks", 3, "ISE"),
    ("Software Engineering", 4, "ISE"),
    ("Cloud Computing", 3, "ISE"),
    # ECE
    ("VLSI", 4, "ECE"),
    ("Signals and Systems", 4, "ECE"),
    ("Embedded Systems", 3, "ECE"),
    ("Communication Theory", 3, "ECE"),
    # MECH
    ("Thermodynamics", 4, "MECH"),
    ("Fluid Mechanics", 4, "MECH"),
    ("Machine Design", 3, "MECH"),
    ("Robotics", 3, "MECH"),
]

assert len(COURSES) == 16, "Must have exactly 16 courses (SDD §7.2)"


def build_database(db_path: str = DB_PATH) -> None:
    """Create college.db from scratch, seeding all three tables."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists():
        path.unlink()

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # ── Create tables (exact schema from SDD §7.1) ─────────────────────────
    cur.executescript("""
        CREATE TABLE students(
            id       INTEGER PRIMARY KEY,
            name     TEXT,
            branch   TEXT,
            semester INTEGER,
            cgpa     REAL,
            city     TEXT
        );

        CREATE TABLE courses(
            course_id   INTEGER PRIMARY KEY,
            course_name TEXT,
            credits     INTEGER,
            branch      TEXT
        );

        CREATE TABLE marks(
            student_id  INTEGER,
            course_id   INTEGER,
            marks       INTEGER,
            attendance  INTEGER,
            FOREIGN KEY(student_id) REFERENCES students(id),
            FOREIGN KEY(course_id)  REFERENCES courses(course_id)
        );
    """)

    # ── Insert 60 students ─────────────────────────────────────────────────
    # Distribute branches evenly (15 per branch)
    # Guarantee Mangaluru students exist
    students = []
    student_id = 1

    for b_idx, branch in enumerate(BRANCHES):
        for s_idx in range(15):
            fn = FIRST_NAMES[(student_id - 1) % len(FIRST_NAMES)]
            sn = SURNAMES[(student_id - 1 + b_idx) % len(SURNAMES)]
            name = f"{fn} {sn}"
            sem = SEMESTERS[s_idx % len(SEMESTERS)]
            cgpa = round(random.uniform(6.00, 9.80), 2)
            # Ensure Mangaluru is well represented
            if s_idx < 3:
                city = "Mangaluru"
            else:
                city = random.choice(CITIES)

            students.append((student_id, name, branch, sem, cgpa, city))
            student_id += 1

    cur.executemany("INSERT INTO students VALUES (?,?,?,?,?,?)", students)

    # ── Insert 16 courses ──────────────────────────────────────────────────
    course_rows = [
        (i + 1, name, credits, branch)
        for i, (name, credits, branch) in enumerate(COURSES)
    ]
    cur.executemany("INSERT INTO courses VALUES (?,?,?,?)", course_rows)

    # ── Insert 240 marks rows (SDD §7.2) ───────────────────────────────────
    # Every student gets a row for each of the 4 courses of their own branch
    branch_course_ids = {}
    for cid, (name, credits, branch) in enumerate(COURSES, start=1):
        branch_course_ids.setdefault(branch, []).append(cid)

    marks_rows = []
    for sid, name, branch, semester, cgpa, city in students:
        cids = branch_course_ids[branch]
        assert len(cids) == 4, f"Branch {branch} must have 4 courses"
        for cid in cids:
            marks = random.randint(30, 100)
            attendance = random.randint(55, 100)
            marks_rows.append((sid, cid, marks, attendance))

    cur.executemany("INSERT INTO marks VALUES (?,?,?,?)", marks_rows)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    build_database(DB_PATH)
    print("college.db built successfully according to SDD §7.2.")
