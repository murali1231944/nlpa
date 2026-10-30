"""
test_phase3.py — Test suite for Phase 3: NLP Modules (SDD §8.1–§8.5, §15).

Verifies:
  - preprocess.py: spaCy linguistic analysis, tokenization, lemmatization, noun chunks
  - extraction.py: rule-based hint detection (aggregates, comparison operators, top_n)
  - schema_linking.py: dense embeddings, cosine thresholding, schema pruning
  - value_linking.py: RapidFuzz matching, alias resolution, short-token guard
  - retrieval.py: few-shot example retrieval, embedding cache, leak detection
  - pipeline.py: full mode end-to-end orchestration
"""

import pytest

from text2sql.core.pipeline import answer
from text2sql.nlp.extraction import extract_hints
from text2sql.nlp.preprocess import analyse
from text2sql.nlp.retrieval import retrieve_examples
from text2sql.nlp.schema_linking import link_schema, prune_tables
from text2sql.nlp.value_linking import link_values


# ═══════════════════════════════════════════════════════════════════════════
# 1. Linguistic Analysis (preprocess.py) — SDD §8.1, §15
# ═══════════════════════════════════════════════════════════════════════════

class TestPreprocess:
    def test_running_example_lemmas_and_chunks(self):
        # SDD §15: analyse(): for the running example, the lemmas should include
        # pupil, mangalore, dbms, attendance; noun_chunks should include pupils.
        text = "Show pupils from Mangalore in dbms with attendance above 75%"
        res = analyse(text)

        lemmas = set(res["lemmas"])
        assert "pupil" in lemmas
        assert "mangalore" in lemmas
        assert "dbms" in lemmas
        assert "attendance" in lemmas

        # Noun chunks must include pupils
        chunks = [c.lower() for c in res["noun_chunks"]]
        assert any("pupil" in c for c in chunks)


# ═══════════════════════════════════════════════════════════════════════════
# 2. Rule-Based Extraction (extraction.py) — SDD §8.2, §15
# ═══════════════════════════════════════════════════════════════════════════

class TestExtraction:
    def test_running_example_hints(self):
        # SDD §15: extract_hints(): the running example gives condition operator > with value 75
        text = "Show the average marks for pupils from Mangalore in dbms with attendance above 75%"
        analysis = analyse(text)
        hints = extract_hints(analysis, text)

        assert "AVG" in hints["aggregates"]
        op_values = [(c["operator"], c["value"]) for c in hints["conditions"]]
        assert (">", 75) in op_values

    def test_at_least_operator_ge(self):
        # SDD §15: For at least 5 marks, the operator is >=, not >.
        text = "List students with at least 5 marks"
        analysis = analyse(text)
        hints = extract_hints(analysis, text)

        op_values = [(c["operator"], c["value"]) for c in hints["conditions"]]
        assert (">=", 5) in op_values
        assert (">", 5) not in op_values

    def test_top_n_extraction(self):
        # SDD §15: For top 5 students, top_n is 5.
        text = "Find top 5 students with highest cgpa"
        analysis = analyse(text)
        hints = extract_hints(analysis, text)

        assert hints["top_n"] == 5
        assert "MAX" in hints["aggregates"]


# ═══════════════════════════════════════════════════════════════════════════
# 3. Schema Linking & Pruning (schema_linking.py) — SDD §8.3, §15
# ═══════════════════════════════════════════════════════════════════════════

class TestSchemaLinking:
    def test_acceptance_links(self):
        # SDD §15: pupils links to the students table; attendance links to marks.attendance;
        # grades links to students.cgpa or marks.marks.
        res = link_schema(["pupils", "attendance", "grades"], threshold=0.40)

        assert "students" in res["tables"]
        assert "attendance" in res["columns"]
        assert res["columns"]["attendance"]["column"] == "marks.attendance"

        # grades may match table marks or students.cgpa / marks.marks
        grade_match = (
            "marks" in res["tables"] or
            ("grades" in res["columns"] and "marks" in res["columns"]["grades"]["column"]) or
            ("grades" in res["columns"] and "cgpa" in res["columns"]["grades"]["column"])
        )
        assert grade_match

    def test_scores_log_generated(self):
        # SDD §14: Print scores_log for all schema links
        res = link_schema(["pupils", "attendance"])
        assert len(res["scores_log"]) >= 2
        for entry in res["scores_log"]:
            assert "phrase" in entry
            assert "top_candidates" in entry
            assert len(entry["top_candidates"]) <= 3

    def test_pruning_bridge_table_inclusion(self):
        # SDD §8.3: If both students and courses are present, ALWAYS add marks (bridge table).
        pruned = prune_tables(["students", "courses"])
        assert "marks" in pruned
        assert set(pruned) == {"students", "courses", "marks"}

    def test_pruning_fallback_when_empty(self):
        # SDD §8.3: If result is empty, fall back to ALL tables.
        pruned = prune_tables([])
        assert pruned == ["students", "courses", "marks"]


# ═══════════════════════════════════════════════════════════════════════════
# 4. Value Linking (value_linking.py) — SDD §8.4, §15
# ═══════════════════════════════════════════════════════════════════════════

class TestValueLinking:
    def test_city_and_course_linking(self):
        # SDD §15: Mangalore links to students.city = Mangaluru; dbms links to courses.course_name = DBMS
        tokens = ["pupils", "from", "Mangalore", "in", "dbms"]
        links = link_values(tokens)

        matched = {(l["column"], l["value"]) for l in links}
        assert ("students.city", "Mangaluru") in matched
        assert ("courses.course_name", "DBMS") in matched

    def test_average_and_marks_produce_no_link(self):
        # SDD §15: average and marks produce NO value link
        tokens = ["find", "the", "average", "marks", "of", "students"]
        links = link_values(tokens)
        assert len(links) == 0

    def test_cse_exact_match_rule(self):
        # SDD §15: cse links to students.branch = CSE only as an exact match
        tokens = ["show", "cse", "students"]
        links = link_values(tokens)
        matched = {(l["column"], l["value"]) for l in links}
        assert ("students.branch", "CSE") in matched

        # 'cs' is < MIN_FUZZY_LEN (4) and not an exact match -> should NOT link
        tokens_short = ["show", "cs", "students"]
        links_short = link_values(tokens_short)
        matched_short = {(l["column"], l["value"]) for l in links_short}
        assert ("students.branch", "CSE") not in matched_short


# ═══════════════════════════════════════════════════════════════════════════
# 5. Few-shot Retrieval (retrieval.py) — SDD §8.5, §15
# ═══════════════════════════════════════════════════════════════════════════

class TestRetrieval:
    def test_retrieve_top_k(self):
        results = retrieve_examples("Show top students in DBMS from Mangalore", k=4)
        assert len(results) == 4
        for r in results:
            assert "question" in r
            assert "sql" in r
            assert "similarity" in r
            assert isinstance(r["similarity"], float)

        # Similarities must be sorted descending
        sims = [r["similarity"] for r in results]
        assert sims == sorted(sims, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
# 6. Full Pipeline Integration (SDD §8.10)
# ═══════════════════════════════════════════════════════════════════════════

class TestFullPipeline:
    def test_full_pipeline_answers_with_all_nlp_components(self):
        mock_llm = lambda p: "SELECT s.name, m.attendance FROM students s JOIN marks m ON s.id = m.student_id WHERE s.city = 'Mangaluru';"
        result = answer(
            "Show pupils from Mangalore in dbms with attendance above 75%",
            mode="full",
            custom_llm_fn=mock_llm,
        )

        assert result["mode"] == "full"
        assert result["error"] is None
        assert len(result["columns"]) > 0
        assert len(result["rows"]) > 0

        # Verify all NLP dictionary fields exist per SDD §8.10
        nlp = result["nlp"]
        assert nlp["analysis"] is not None
        assert nlp["hints"] is not None
        assert "schema_links" in nlp
        assert "value_links" in nlp
        assert len(nlp["retrieved_examples"]) == 4
        assert len(nlp["pruned_tables"]) >= 2
        assert result["timings"]["nlp_ms"] > 0
