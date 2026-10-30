"""
review_phase3.py — Generate Phase 3 inspection outputs for human review (SDD §14, §15).

Outputs:
  1. scores_log for sample phrases in schema linking
  2. RapidFuzz scores for colonial city name variants
  3. Top-4 retrieved examples for 5 sample questions
"""

from rapidfuzz import fuzz
from text2sql.nlp.schema_linking import link_schema
from text2sql.nlp.value_linking import CITY_ALIASES
from text2sql.nlp.retrieval import retrieve_examples


def run_review():
    print("=" * 70)
    print("1. SCHEMA-LINKING SCORES_LOG (SDD §14 Phase 3)")
    print("=" * 70)
    sample_phrases = ["pupils", "attendance", "grades", "city", "course name", "cgpa", "marks", "students"]
    res = link_schema(sample_phrases)
    for log in res["scores_log"]:
        status = "ACCEPTED" if log["accepted"] else "REJECTED"
        print(f"Phrase: '{log['phrase']:<12}' -> Best: {log['best_target']:<18} Score: {log['best_score']:.4f}  [{status}]")
        print("  Top candidates:")
        for cand in log["top_candidates"]:
            print(f"    - {cand['target']:<20}: {cand['score']:.4f}")
        print()

    print("=" * 70)
    print("2. FUZZY-MATCH SCORES FOR CITY VARIANTS (SDD §14 Phase 3)")
    print("=" * 70)
    pairs = [
        ("Mangalore", "Mangaluru"),
        ("Bangalore", "Bengaluru"),
        ("Mysore", "Mysuru"),
        ("Shimoga", "Shivamogga"),
        ("Belgaum", "Belagavi"),
    ]
    for p, s in pairs:
        score = fuzz.ratio(p.lower(), s.lower())
        alias = CITY_ALIASES.get(p.lower(), "None")
        print(f"'{p}' vs '{s}': RapidFuzz ratio = {score:.1f} | Alias Map Target = '{alias}'")
    print()

    print("=" * 70)
    print("3. RETRIEVED EXAMPLES FOR 5 SAMPLE QUESTIONS (SDD §14 Phase 3)")
    print("=" * 70)
    sample_qs = [
        "Show pupils from Mangalore in dbms with attendance above 75%",
        "Count the total number of students in CSE branch",
        "What is the highest cgpa among students in Bengaluru?",
        "List all courses with more than 3 credits",
        "Show the average marks obtained in DBMS course",
    ]
    for q in sample_qs:
        print(f"Query: \"{q}\"")
        exs = retrieve_examples(q, k=4)
        for i, ex in enumerate(exs, 1):
            print(f"  [{i}] (similarity: {ex['similarity']:.4f})")
            print(f"      Example Q  : {ex['question']}")
            print(f"      Example SQL: {ex['sql']}")
        print()


if __name__ == "__main__":
    run_review()
