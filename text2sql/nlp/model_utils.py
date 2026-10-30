"""
model_utils.py — Shared helper for loading sentence-transformers models (SDD §8.3, §8.5).

Attempts to load with local_files_only=True first to avoid external network/hub
metadata checks (e.g. in sandboxed or offline environments), falling back to a
standard online download if the model is not yet cached locally.
"""

from sentence_transformers import SentenceTransformer
from text2sql.config import EMBED_MODEL


def load_embedding_model(model_name: str = EMBED_MODEL) -> SentenceTransformer:
    """
    Load a SentenceTransformer model with offline-first fallback logic.
    """
    try:
        return SentenceTransformer(model_name, local_files_only=True)
    except Exception:
        return SentenceTransformer(model_name, local_files_only=False)

