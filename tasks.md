# Task Tracker — NLP-Powered Text-to-SQL Interface

## Legend
- `[ ]` not started
- `[~]` in progress
- `[x]` done
- `[!]` blocked — waiting on human input

## Progress: Phases 1-3 code-complete; Groq migration validation and Phase 3 acceptance reviews pending

---

## Phase 1 — Foundation
*Done when: one LLM test call returns text AND the database passes Section 15 checks.*

| Status | Task | Owner | Result / Date |
|--------|------|-------|---------------|
| [x] | Create folder structure (db/, data/, nlp/, evaluation/, tests/, pipeline/) | Agent | Done (2026-10-28) |
| [x] | Write requirements.txt | Agent | Done (2026-10-28) |
| [x] | Write .env.example (GROQ_API_KEY, GROQ_MODEL placeholders only) | Agent | Updated for Groq (2026-10-28) |
| [x] | Write config.py (load .env; expose API key, model name, all thresholds) | Agent | Done (2026-10-28) |
| [x] | Write db/create_db.py (seed 60 students, 16 courses, 240 marks rows) | Agent | PASS (2026-10-28) |
| [x] | Acceptance check: DB has 60 students, 16 courses, 240 marks rows; Mangaluru in students.city; DBMS in courses.course_name | Agent | PASS (2026-10-28) |
| [x] | Write db/schema_utils.py (schema text formatter + relations line) | Agent | PASS (2026-10-28) |
| [x] | Write loaders for data/examples.json and data/test_questions.json | Agent | PASS (2026-10-28) |
| [x] | Confirm examples.json format (field names: question, sql, etc.) | Human | Confirmed (2026-10-28) |
| [x] | Confirm test_questions.json format (field names: question, gold_sql, level, messy, etc.) | Human | Confirmed (2026-10-28) |
| [x] | Supply data/examples.json (40 question-SQL pairs) | Agent | 40 pairs drafted & tested (2026-10-28) |
| [!] | Supply data/test_questions.json (15 questions + gold SQL + difficulty) | Human | Pending human creation |
| [x] | Confirm Groq model for the project client | Human | `openai/gpt-oss-120b` from working `test.py` setup |
| [x] | Run one test LLM call and confirm text is returned | Agent | PASS: "LLM test call successful" (2026-10-28) |
| [x] | Write tests/test_phase1.py and confirm all pass | Agent | 23/23 PASS (2026-10-28) |

---

## Phase 2 — Baseline (Code complete; phase status recorded separately)
*Done when: a CLI question returns an answer AND unsafe SQL is blocked. The tracker records the checks as passing; a successful live API test was previously reported and was not rerun during documentation reconciliation.*

| Status | Task | Owner | Result / Date |
|--------|------|-------|---------------|
| [x] | Write pipeline/client.py (Groq API call + disk cache) | Agent | Migrated to Groq; validation pending |
| [~] | Verify Groq client through the app pipeline | Agent | Awaiting live smoke check; user-reported `test.py` call succeeded |
| [x] | Write pipeline/validator.py (regex safety layer — block non-SELECT and destructive SQL) | Agent | Done (2026-10-28) |
| [x] | Write pipeline/executor.py (read-only SQLite connection) | Agent | Done (2026-10-28) |
| [x] | Write pipeline/prompt_builder.py — baseline version (schema text + question only) | Agent | Done (2026-10-28) |
| [x] | Wire baseline pipeline end-to-end with one retry on SQL error | Agent | Done (2026-10-28) |
| [x] | Acceptance check: validator blocks DROP TABLE, multi-statement DELETE, UPDATE SET | Agent | PASS (2026-10-28) |
| [x] | Acceptance check: validator allows normal SELECT and SELECT whose literal contains "update" | Agent | PASS (2026-10-28) |
| [x] | Acceptance check: executor raises error on write attempt via read-only connection | Agent | PASS (2026-10-28) |
| [x] | Acceptance check: broken query triggers exactly 1 retry; zero-row result triggers 0 retries | Agent | PASS (2026-10-28) |
| [x] | Write tests/test_phase2.py and confirm all pass | Agent | 24/24 PASS (2026-10-28) |

---

## Phase 3 — NLP Modules (Code complete; phase-incomplete)
*Done when: each module passes its own tests AND full pipeline runs on all 15 questions
AND human has inspected prompts, scores, and retrieved examples. (Status: Code complete; human reviews and acceptance checks pending)*

| Status | Task | Owner | Result / Date |
|--------|------|-------|---------------|
| [x] | Write nlp/preprocess.py (spaCy tokenise, lemmatise, POS, noun chunks) | Agent | Done (2026-10-28) |
| [x] | Acceptance check: analyse() on running example produces lemmas pupil, mangalore, dbms, attendance; noun_chunks includes pupils | Agent | PASS (2026-10-28) |
| [x] | Write nlp/extraction.py (aggregate keywords, condition operators, numeric values, top_n) | Agent | Done (2026-10-28) |
| [x] | Acceptance check: extract_hints() gives AVG + condition > with value 75 for running example | Agent | PASS (2026-10-28) |
| [x] | Acceptance check: "at least 5 marks" gives operator >= (not >); "top 5 students" gives top_n=5 | Agent | PASS (2026-10-28) |
| [x] | Write nlp/schema_linking.py (Sentence-Transformers + cosine, schema descriptions, table pruning) | Agent | Done (2026-10-28) |
| [x] | Acceptance check: pupils -> students; attendance -> marks.attendance; grades -> students.cgpa or marks.marks | Agent | PASS (2026-10-28) |
| [x] | Print scores_log for all schema links | Agent | Printed (2026-10-28) |
| [!] | Review scores_log and decide schema-linking threshold value | Human | Ready for human confirmation (score: 0.40) |
| [x] | Write nlp/value_linking.py (RapidFuzz fuzzy matching against cell values) | Agent | Done (2026-10-28) |
| [x] | Print fuzzy-match scores for: Mangalore/Mangaluru, Bangalore/Bengaluru, Mysore/Mysuru | Agent | Printed (2026-10-28) |
| [!] | Review fuzzy scores and decide whether alias map is needed | Human | Ready for human confirmation |
| [x] | Acceptance check: Mangalore -> students.city=Mangaluru; dbms -> courses.course_name=DBMS | Agent | PASS (2026-10-28) |
| [x] | Acceptance check: average and marks produce NO value link; cse links only as exact match | Agent | PASS (2026-10-28) |
| [x] | Write nlp/retrieval.py (sentence-transformer embeddings, top-4 retrieval, leak check) | Agent | Done (2026-10-28) |
| [x] | Print retrieved examples for 5 sample questions | Agent | Printed (2026-10-28) |
| [!] | Read 4 retrieved examples for each of 5 sample questions and confirm relevance; leak check passes | Human | Ready for human confirmation |
| [x] | Write nlp/model_utils.py (shared offline-first model loader with local_files_only fallback) | Agent | 60/60 PASS both offline & online (2026-10-28) |
| [x] | Integrate NLP modules into full pipeline (full mode) | Agent | Done (2026-10-28) |
| [!] | Run full pipeline on all 15 test questions; human inspects prompts | Agent | Awaiting test_questions.json from human |
| [!] | Inspect prompts for all 15 questions and confirm they look correct | Human | Awaiting test_questions.json from human |
| [x] | Write tests/test_phase3.py and confirm all pass | Agent | 13/13 PASS (2026-10-28) |

---

## Phase 4 — Interface
*Done when: live demo works including a messy question and a malicious one.*

| Status | Task | Owner | Result / Date |
|--------|------|-------|---------------|
| [ ] | Write app.py (Streamlit UI: text box, Ask button, schema sidebar, example questions) | Agent | |
| [ ] | Add NLP analysis panel (tokens/lemmas, POS, noun chunks, aggregates, conditions, schema links with scores, value links with scores, retrieved examples with similarity, pruned tables, full prompt) | Agent | |
| [ ] | Add mode switch (full vs baseline) | Agent | |
| [ ] | Acceptance check: demo works for a messy question (e.g. "pupils from Mangalore in dbms") | Agent | |
| [ ] | Acceptance check: demo blocks a malicious query and shows clear warning | Agent | |
| [ ] | Acceptance check: errors never show a raw stack trace | Agent | |

---

## Phase 5 — Evaluation
*Done when: summary.json and the results/error table exist.*

| Status | Task | Owner | Result / Date |
|--------|------|-------|---------------|
| [ ] | Write evaluation/metrics.py (execution accuracy, table recall, column recall, value recall/precision, cost) | Agent | |
| [ ] | Write evaluation/evaluate.py (run 15 questions in full mode and baseline mode, save to data/results/) | Agent | |
| [ ] | Acceptance check: summary.json exists; results table and error list exist | Agent | |
| [ ] | Integrity check: test set never used in prompts or examples; thresholds tuned only from scores_log | Agent | |

---

## Phase 6 — Documentation
*Done when: a new person can reproduce everything from the README.*

| Status | Task | Owner | Result / Date |
|--------|------|-------|---------------|
| [ ] | Finalise README.md with all real results, observations, and work log | Agent | |
| [ ] | Write architecture diagram (ASCII or image) | Agent | |
| [ ] | Write results write-up (summary.json findings in plain language) | Agent | |
| [ ] | Verify CHANGELOG.md is complete | Agent | |
| [ ] | Human reads README and confirms reproducibility | Human | |

---

## Blocked / Needs Human Input

| Item | Waiting for |
|------|-------------|
| data/test_questions.json | Human to supply 15 questions + gold SQL + difficulty |
| Schema-linking threshold | Human to review `scores_log` and confirm threshold |
| Value-linking scores / aliases | Human to review fuzzy scores and decide whether the alias map is appropriate |
| Retrieved examples | Human to confirm relevance and leak-check results |
| Phase 3 full run and prompts | Awaiting the human-authored test set and human review |

---

## Open Questions

| # | Question | Status |
|---|----------|--------|
| 3 | Which sentence-transformer model to use for retrieval? (default: all-MiniLM-L6-v2) | Open |
| 4 | Schema-linking threshold — to be set after human reviews scores_log in Phase 3 | Open |
| 6 | Is an alias map needed for Mangalore/Mangaluru etc.? — human decides in Phase 3 | Open |
