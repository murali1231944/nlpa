"""
step1_review.py — Schema linking detailed inspection (Review Item 1).
"""

from text2sql.nlp.preprocess import analyse
from text2sql.nlp.schema_linking import link_schema


def run():
    print("=" * 70)
    print("1(a) PHRASES THAT SHOULD NOT LINK (SCHEMA_LINK_THRESHOLD = 0.40)")
    print("=" * 70)
    non_link_phrases = ["average", "above", "show", "list", "many", "each"]
    res_a = link_schema(non_link_phrases, threshold=0.40)
    for log in res_a["scores_log"]:
        status = "ACCEPTED" if log["accepted"] else "REJECTED (CORRECT)"
        print(f"Phrase: '{log['phrase']:<10}' -> Best: {log['best_target']:<18} Score: {log['best_score']:.4f}  [{status}]")
        print("  Top candidates:")
        for cand in log["top_candidates"]:
            print(f"    - {cand['target']:<20}: {cand['score']:.4f}")
        print()

    print("=" * 70)
    print("1(b) SYNONYMS FOR STUDENTS: learners, scholars, candidates")
    print("=" * 70)
    student_synonyms = ["learners", "scholars", "candidates"]
    res_b = link_schema(student_synonyms, threshold=0.40)
    for log in res_b["scores_log"]:
        status = "ACCEPTED" if log["accepted"] else "REJECTED"
        print(f"Phrase: '{log['phrase']:<10}' -> Best: {log['best_target']:<18} Score: {log['best_score']:.4f}  [{status}]")
        print("  Top candidates:")
        for cand in log["top_candidates"]:
            print(f"    - {cand['target']:<20}: {cand['score']:.4f}")
        print()

    print("=" * 70)
    print("1(c) RUNNING EXAMPLE: EVERY NOUN CHUNK (ACCEPTED & REJECTED)")
    print("=" * 70)
    q = "Show pupils from Mangalore in dbms with attendance above 75%"
    analysis = analyse(q)
    print(f"Question: \"{q}\"")
    print(f"Extracted noun chunks: {analysis['noun_chunks']}")
    print(f"Extracted lemmas     : {analysis['lemmas']}\n")

    # Link schema on noun chunks + lemmas
    candidate_phrases = analysis["noun_chunks"] + analysis["lemmas"]
    res_c = link_schema(candidate_phrases, threshold=0.40)
    for log in res_c["scores_log"]:
        status = "ACCEPTED" if log["accepted"] else "REJECTED"
        print(f"Candidate: '{log['phrase']:<15}' -> Best: {log['best_target']:<18} Score: {log['best_score']:.4f}  [{status}]")
        print("  Top candidates:")
        for cand in log["top_candidates"]:
            print(f"    - {cand['target']:<20}: {cand['score']:.4f}")
        print()


if __name__ == "__main__":
    run()
