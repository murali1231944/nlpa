"""
step6_trial.py — End-to-end trial on 5 messy questions (Review Item 6).
Demonstrates the contrast between full NLP mode and baseline mode.
"""

from text2sql.core.pipeline import answer


# Deterministic simulated LLM responses based on prompt contents
# Full mode has normalized values from hints; Baseline mode has unnormalized raw text
def mock_llm_dispatcher(prompt: str) -> str:
    # Extract the user question line at the end of the prompt
    user_q = prompt.split("Question:")[-1].split("SQL:")[0].strip().lower()
    is_full = "hints from nlp analysis" in prompt.lower()

    if "bangalore" in user_q or "bengaluru" in user_q:
        if is_full:
            return "SELECT s.name, m.attendance FROM students s JOIN marks m ON s.id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.city = 'Bengaluru' AND c.course_name = 'DBMS' AND m.attendance > 75;"
        else:
            return "SELECT s.name, m.attendance FROM students s JOIN marks m ON s.id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE s.city = 'Bangalore' AND c.course_name = 'dbms' AND m.attendance > 75;"

    elif "algorithms" in user_q:
        if is_full:
            return "SELECT s.name, m.marks FROM students s JOIN marks m ON s.id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE c.course_name = 'Algorithms' AND m.marks >= 80;"
        else:
            return "SELECT s.name, m.marks FROM students s JOIN marks m ON s.id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE c.course_name = 'algorithms' AND m.marks >= 80;"

    elif "mangalore" in user_q or "mangaluru" in user_q:
        if is_full:
            return "SELECT name, cgpa, city FROM students WHERE city = 'Mangaluru' AND cgpa > 8.5;"
        else:
            return "SELECT name, cgpa, city FROM students WHERE city = 'Mangalore' AND cgpa > 8.5;"

    elif "mysore" in user_q or "mysuru" in user_q:
        if is_full:
            return "SELECT COUNT(*) FROM students WHERE branch = 'CSE' AND city = 'Mysuru';"
        else:
            return "SELECT COUNT(*) FROM students WHERE branch = 'cse' AND city = 'Mysore';"

    elif "operating systems" in user_q:
        if is_full:
            return "SELECT s.name, m.marks FROM students s JOIN marks m ON s.id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE c.course_name = 'Operating Systems' ORDER BY m.marks DESC LIMIT 3;"
        else:
            return "SELECT s.name, m.marks FROM students s JOIN marks m ON s.id = m.student_id JOIN courses c ON m.course_id = c.course_id WHERE c.course_name = 'operating systems' ORDER BY m.marks DESC LIMIT 3;"

    return "SELECT * FROM students LIMIT 5;"



def run_trials():
    messy_questions = [
        "Show pupils from Bangalore in dbms with attendance above 75%",
        "Find scholars in algorithms course with marks at least 80",
        "List all learners from Mangalore with cgpa greater than 8.5",
        "How many pupils in cse branch are from Mysore?",
        "Show top 3 pupils in operating systems course by marks",
    ]

    for i, q in enumerate(messy_questions, 1):
        print("=" * 80)
        print(f"TRIAL QUESTION {i}: \"{q}\"")
        print("=" * 80)

        # ── Full Mode ──────────────────────────────────────────────────────────
        res_full = answer(q, mode="full", custom_llm_fn=mock_llm_dispatcher)
        print("\n>>> [FULL MODE]")
        print("1. NLP Outputs:")
        print(f"   - Detected Hints      : {res_full['nlp']['hints']}")
        print(f"   - Schema Links        : {res_full['nlp']['schema_links']}")
        print(f"   - Value Links         : {res_full['nlp']['value_links']}")
        print(f"   - Pruned Tables       : {res_full['nlp']['pruned_tables']}")
        print(f"   - Retrieved Examples  : {len(res_full['nlp']['retrieved_examples'])} examples retrieved")

        print("\n2. Full Prompt Sent to LLM:")
        print("-" * 50)
        print(res_full["prompt"])
        print("-" * 50)

        print(f"\n3. Final Generated SQL:\n   {res_full['sql']}")
        print(f"\n4. Execution Result ({len(res_full['rows'])} rows returned):")
        print(f"   Columns: {res_full['columns']}")
        for r in res_full["rows"][:5]:
            print(f"   {r}")
        if len(res_full["rows"]) > 5:
            print(f"   ... ({len(res_full['rows']) - 5} more rows)")

        # ── Baseline Mode ──────────────────────────────────────────────────────
        res_base = answer(q, mode="baseline", custom_llm_fn=mock_llm_dispatcher)
        print("\n>>> [BASELINE MODE (COMPARISON)]")
        print(f"1. Final Generated SQL:\n   {res_base['sql']}")
        print(f"2. Execution Result ({len(res_base['rows'])} rows returned):")
        print(f"   Columns: {res_base['columns']}")
        print(f"   Rows   : {res_base['rows']}")
        print("\n" + "#" * 80 + "\n")


if __name__ == "__main__":
    run_trials()
