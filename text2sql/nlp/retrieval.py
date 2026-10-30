"""
retrieval.py — Few-shot example retrieval using sentence-transformers (SDD §8.5, §15).

Demonstrates:
  - Dense semantic retrieval using pre-computed embeddings
  - Cosine similarity ranking
  - Data integrity & leakage detection against test set
  - Automatic index caching and invalidation
"""

from pathlib import Path
from typing import Any
import numpy as np

from text2sql.config import EMBED_FILE, EMBED_MODEL, EXAMPLES_PATH, TEST_Q_PATH, TOP_K_EXAMPLES
from text2sql.data.loaders import load_examples
from text2sql.nlp.model_utils import load_embedding_model

_RETRIEVER_MODEL = None


def _get_retriever_model():
    """Lazily load the sentence transformer model."""
    global _RETRIEVER_MODEL
    if _RETRIEVER_MODEL is None:
        _RETRIEVER_MODEL = load_embedding_model(EMBED_MODEL)
    return _RETRIEVER_MODEL


def build_index() -> np.ndarray:
    """
    Encode all example questions and save to data/example_embeddings.npy (SDD §8.5).
    Runs data integrity and leakage check against test questions.
    """
    examples = load_examples(EXAMPLES_PATH)
    questions = [ex["question"] for ex in examples]

    model = _get_retriever_model()
    embeddings = model.encode(questions, normalize_embeddings=True)

    # Save embeddings to disk
    embed_path = Path(EMBED_FILE)
    embed_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(str(embed_path), embeddings)

    # Leak check (SDD §8.5): compare against test_questions.json if present
    test_file = Path(TEST_Q_PATH)
    if test_file.exists():
        import json
        try:
            with open(test_file, "r", encoding="utf-8-sig") as f:
                test_data = json.load(f)
            test_questions = [item.get("question", "").strip() for item in test_data if item.get("question")]
            if test_questions:
                check_and_report_leakage(test_questions, questions, embeddings)
        except Exception as e:
            if "DATA LEAK DETECTED" in str(e):
                raise
            print(f"Note on leak check: {e}")

    return embeddings


def check_and_report_leakage(
    test_questions: list[str],
    example_questions: list[str] | None = None,
    example_embeddings: np.ndarray | None = None,
    warning_threshold: float = 0.85,
) -> list[dict[str, Any]]:
    """
    Check test questions against the example library.
    Raises ValueError on exact match.
    Returns list of dicts with highest similarity per test question:
      [{'test_question': str, 'most_similar_example': str, 'similarity': float, 'warning': bool}]
    """
    if example_questions is None:
        examples = load_examples(EXAMPLES_PATH)
        example_questions = [ex["question"] for ex in examples]

    model = _get_retriever_model()
    if example_embeddings is None:
        embed_path = Path(EMBED_FILE)
        if embed_path.exists():
            example_embeddings = np.load(str(embed_path))
        else:
            example_embeddings = model.encode(example_questions, normalize_embeddings=True)

    # 1. Exact match check (case-insensitive)
    example_lower = {q.lower(): q for q in example_questions}
    for tq in test_questions:
        if tq.lower() in example_lower:
            raise ValueError(
                f"DATA LEAK DETECTED: Test question exactly matches an example: '{tq}'"
            )

    # 2. Similarity analysis (warning at > 0.85)
    report = []
    if test_questions:
        test_embeddings = model.encode(test_questions, normalize_embeddings=True)
        sim_matrix = np.dot(test_embeddings, example_embeddings.T)

        for t_idx, row in enumerate(sim_matrix):
            max_sim = float(np.max(row))
            ex_idx = int(np.argmax(row))
            is_warning = max_sim >= warning_threshold

            item = {
                "test_question": test_questions[t_idx],
                "most_similar_example": example_questions[ex_idx],
                "similarity": round(max_sim, 4),
                "warning": is_warning,
            }
            report.append(item)

            if is_warning:
                print(
                    f"WARNING: High similarity ({max_sim:.3f} >= {warning_threshold}) between test question '{test_questions[t_idx]}' "
                    f"and example question '{example_questions[ex_idx]}'"
                )

    return report



def retrieve_examples(question: str, k: int = TOP_K_EXAMPLES) -> list[dict[str, Any]]:
    """
    Encode the query question and retrieve top-k similar solved examples by cosine similarity.

    Args:
        question: Plain-English query question.
        k: Number of examples to return (default from config.TOP_K_EXAMPLES).

    Returns:
        list of dicts: [
            {'id': int, 'question': str, 'sql': str, 'similarity': float}, ...
        ]
    """
    examples = load_examples(EXAMPLES_PATH)
    embed_path = Path(EMBED_FILE)

    # Rebuild index automatically if missing or example count changed
    if not embed_path.exists():
        embeddings = build_index()
    else:
        try:
            embeddings = np.load(str(embed_path))
            if len(embeddings) != len(examples):
                embeddings = build_index()
        except Exception:
            embeddings = build_index()

    model = _get_retriever_model()
    q_vec = model.encode([question.strip()], normalize_embeddings=True)[0]

    # Cosine similarity via dot product on normalized vectors
    similarities = np.dot(embeddings, q_vec)

    # Sort in descending order
    top_indices = np.argsort(similarities)[::-1][:k]

    results = []
    for idx in top_indices:
        ex = examples[int(idx)]
        results.append({
            "id": ex.get("id"),
            "question": ex.get("question"),
            "sql": ex.get("sql"),
            "tags": ex.get("tags", []),
            "similarity": round(float(similarities[idx]), 4),
        })

    return results
