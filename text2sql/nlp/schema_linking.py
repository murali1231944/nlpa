"""
schema_linking.py — Semantic schema linking and table pruning (SDD §8.3, §15).

Demonstrates:
  - Dense text embeddings (sentence-transformers)
  - Cosine similarity via normalized dot products
  - Candidate phrase extraction and thresholded linking
  - Schema pruning with mandatory bridge table inclusion
"""

import numpy as np
from text2sql.config import EMBED_MODEL, SCHEMA_LINK_THRESHOLD
from text2sql.nlp.model_utils import load_embedding_model

# Hand-crafted schema descriptions embedded once at module import (SDD §8.3)
SCHEMA_DESCRIPTIONS = {
    "table students": "students pupils learners scholars people enrolled in the college",
    "table courses": "courses subjects papers modules taught",
    "table marks": "marks scores results grades obtained in exams per student per course",
    "students.id": "student id roll number identifier",
    "students.name": "student name full name person",
    "students.branch": "branch department stream discipline",
    "students.semester": "semester sem term year of study",
    "students.cgpa": "cgpa gpa grade point average overall academic performance",
    "students.city": "city town hometown place location native",
    "courses.course_id": "course id code identifier",
    "courses.course_name": "course name subject name paper title",
    "courses.credits": "credits credit points weightage",
    "courses.branch": "branch department offering the course",
    "marks.marks": "marks score points obtained exam result",
    "marks.attendance": "attendance presence classes attended percentage present",
}

_MODEL = None
_KEYS = list(SCHEMA_DESCRIPTIONS.keys())
_DESCRIPTIONS = list(SCHEMA_DESCRIPTIONS.values())
_DESC_EMBEDDINGS = None


def _get_model():
    """Lazily load the sentence transformer model and embed schema descriptions."""
    global _MODEL, _DESC_EMBEDDINGS
    if _MODEL is None:
        _MODEL = load_embedding_model(EMBED_MODEL)
        _DESC_EMBEDDINGS = _MODEL.encode(_DESCRIPTIONS, normalize_embeddings=True)
    return _MODEL, _DESC_EMBEDDINGS


def link_schema(
    phrases: list[str],
    threshold: float = SCHEMA_LINK_THRESHOLD,
) -> dict:
    """
    Link candidate phrases (noun chunks and lemmas) to database tables and columns.

    Args:
        phrases: List of candidate strings from linguistic analysis.
        threshold: Minimum cosine similarity required to accept a link.

    Returns:
        dict with:
          'columns': dict mapping phrase -> {'column': str, 'score': float}
          'tables': sorted list of unique linked table names
          'scores_log': list of dicts with top-3 candidate scores per phrase
    """
    model, desc_embeddings = _get_model()

    # Filter candidate phrases: skip < 3 chars or purely numeric (SDD §8.3)
    cleaned_phrases = []
    seen = set()
    for p in phrases:
        s = p.strip().lower()
        if len(s) >= 3 and not s.replace(".", "").isdigit() and s not in seen:
            seen.add(s)
            cleaned_phrases.append(s)

    if not cleaned_phrases:
        return {"columns": {}, "tables": [], "scores_log": []}

    phrase_embeddings = model.encode(cleaned_phrases, normalize_embeddings=True)

    linked_columns = {}
    linked_tables = set()
    scores_log = []

    # Cosine similarities via dot product on normalized vectors
    sim_matrix = np.dot(phrase_embeddings, desc_embeddings.T)

    for i, phrase in enumerate(cleaned_phrases):
        scores = sim_matrix[i]
        top_indices = np.argsort(scores)[::-1][:3]

        top_candidates = [
            {"target": _KEYS[idx], "score": round(float(scores[idx]), 4)}
            for idx in top_indices
        ]

        best_target = top_candidates[0]["target"]
        best_score = top_candidates[0]["score"]

        accepted = best_score >= threshold
        scores_log.append({
            "phrase": phrase,
            "accepted": accepted,
            "best_target": best_target,
            "best_score": best_score,
            "top_candidates": top_candidates,
        })

        if accepted:
            if best_target.startswith("table "):
                tbl = best_target.replace("table ", "").strip()
                linked_tables.add(tbl)
            else:
                linked_columns[phrase] = {"column": best_target, "score": best_score}
                tbl = best_target.split(".")[0]
                linked_tables.add(tbl)

    return {
        "columns": linked_columns,
        "tables": sorted(list(linked_tables)),
        "scores_log": scores_log,
    }


def prune_tables(
    schema_linked_tables: list[str],
    value_linked_tables: list[str] | None = None,
) -> list[str]:
    """
    Apply SDD §8.3 pruning rules:
      - Tables = schema tables + value tables.
      - If both students and courses are present, ALWAYS add marks (bridge table).
      - If result is empty, fall back to all tables ['students', 'courses', 'marks'].
    """
    tables = set(schema_linked_tables or [])
    if value_linked_tables:
        tables.update(value_linked_tables)

    if "students" in tables and "courses" in tables:
        tables.add("marks")

    if not tables:
        return ["students", "courses", "marks"]

    # Keep deterministic canonical order
    order = ["students", "courses", "marks"]
    return [t for t in order if t in tables]
