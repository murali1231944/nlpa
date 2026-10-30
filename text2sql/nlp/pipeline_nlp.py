"""
pipeline_nlp.py — Orchestrates all Phase 3 NLP modules for full mode (SDD §8.10).

Stages:
  1. preprocess.analyse() -> tokens, lemmas, POS tags, noun chunks
  2. extraction.extract_hints() -> aggregates, conditions, top_n
  3. schema_linking.link_schema() -> column/table links + scores_log
  4. value_linking.link_values() -> cell value links + fuzzy scores
  5. retrieval.retrieve_examples() -> top-k few-shot examples
  6. schema_linking.prune_tables() -> pruned schema text
"""

from typing import Any

from text2sql.db.schema_utils import get_schema_text
from text2sql.nlp.extraction import extract_hints
from text2sql.nlp.preprocess import analyse
from text2sql.nlp.retrieval import retrieve_examples
from text2sql.nlp.schema_linking import link_schema, prune_tables
from text2sql.nlp.value_linking import link_values


def run_nlp_stages(question: str) -> dict[str, Any]:
    """
    Execute all NLP stages on the question for full pipeline mode.

    Returns dict with:
      - 'nlp': dictionary with analysis, hints, schema_links, value_links,
               retrieved_examples, pruned_tables
      - 'hints': formatted hints dictionary for prompt_builder
      - 'examples': list of retrieved examples for prompt_builder
      - 'schema_text': pruned schema text string for prompt_builder
    """
    # 1. Linguistic analysis
    analysis = analyse(question)

    # 2. Extract hint rules (aggregates, conditions, top-N)
    hint_data = extract_hints(analysis, question)

    # 3. Schema linking on noun chunks + lemmas
    candidate_phrases = analysis["noun_chunks"] + analysis["lemmas"]
    schema_res = link_schema(candidate_phrases)

    # 4. Value linking on tokens
    value_links = link_values(analysis["tokens"])

    # 5. Few-shot example retrieval
    examples = retrieve_examples(question)

    # 6. Table pruning
    value_tables = [v["column"].split(".")[0] for v in value_links if "." in v.get("column", "")]
    pruned = prune_tables(schema_res["tables"], value_tables)
    schema_text = get_schema_text(tables=pruned)

    # Format hints for prompt_builder
    hints_for_prompt = {
        "aggregates": hint_data.get("aggregates", []),
        "conditions": hint_data.get("conditions", []),
        "top_n": hint_data.get("top_n"),
        "columns": [v["column"] for v in schema_res["columns"].values()],
        "values": [{"column": v["column"], "value": v["value"]} for v in value_links],
    }

    nlp_payload = {
        "analysis": analysis,
        "hints": hint_data,
        "schema_links": schema_res["columns"],
        "schema_tables": schema_res["tables"],
        "scores_log": schema_res["scores_log"],
        "value_links": value_links,
        "retrieved_examples": examples,
        "pruned_tables": pruned,
    }

    return {
        "nlp": nlp_payload,
        "hints": hints_for_prompt,
        "examples": examples,
        "schema_text": schema_text,
    }


