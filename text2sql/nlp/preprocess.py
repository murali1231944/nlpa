"""
preprocess.py — Linguistic analysis using spaCy (SDD §8.1, §15).

Demonstrates:
  - Tokenisation
  - Lemmatisation
  - Part-of-speech (POS) tagging
  - Noun chunk / phrase extraction
"""

from typing import Any
import spacy

# Load spaCy pipeline once at module load
_NLP = None


def get_nlp_pipeline():
    """Lazily load and cache the en_core_web_sm pipeline."""
    global _NLP
    if _NLP is None:
        _NLP = spacy.load("en_core_web_sm")
    return _NLP


def analyse(question: str) -> dict[str, Any]:
    """
    Run linguistic analysis on a natural language question.

    Args:
        question: Plain-English user question string.

    Returns:
        dict with:
          'tokens': list[str] — individual tokens
          'lemmas': list[str] — lowercased lemmatized tokens
          'pos': list[tuple[str, str]] — (token, POS tag) pairs
          'noun_chunks': list[str] — extracted noun phrases
    """
    nlp = get_nlp_pipeline()
    doc = nlp(question.strip())

    tokens = [token.text for token in doc]
    lemmas = [token.lemma_.lower() for token in doc]
    pos_tags = [(token.text, token.pos_) for token in doc]
    noun_chunks = [chunk.text.strip() for chunk in doc.noun_chunks]

    return {
        "tokens": tokens,
        "lemmas": lemmas,
        "pos": pos_tags,
        "noun_chunks": noun_chunks,
    }
