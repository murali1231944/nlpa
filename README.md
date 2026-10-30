# NLP-Powered Text-to-SQL Interface

A university coursework project that lets a user type a plain-English question
and get back a SQL result from a local SQLite database - no SQL knowledge
required.

> **Single source of truth:** `SDD NLP-Powered Text-to-SQL Interface.pdf` (and `SDD.md`)
> **Task tracker:** [tasks.md](tasks.md)
> **Change log:** [CHANGELOG.md](CHANGELOG.md)
> **Beginner-friendly design and demo guide:** [PROJECT_GUIDE.md](PROJECT_GUIDE.md)

---

## 1. Project Overview

The system accepts natural-language questions such as:

> *"Show the top 5 students in DBMS from Mangalore with attendance above 75%"*

It pre-processes the text with spaCy, extracts hints (aggregates, conditions,
value links, schema links), retrieves similar solved examples, builds a prompt,
calls the Groq LLM, validates and executes the returned SQL, and displays
the result in a Streamlit web UI.

The NLP front-end matters because questions contain messy tokens - informal
words like *pupils*, city-name variants like *Mangalore/Mangaluru*, and
ambiguous terms like *grades* - that a bare LLM prompt would handle poorly
without pre-processing context.

---

## 2. Architecture Summary

```
User question (Streamlit UI)
        |
        v
  preprocess.py       <- spaCy: tokenise, lemmatise, POS-tag, noun chunks
        |
        v
  extraction.py       <- detect aggregates, conditions, numeric values
        |
        v
  schema_linking.py   <- sentence-transformers embeddings -> map tokens to tables/columns
        |
        v
  value_linking.py    <- RapidFuzz fuzzy -> map tokens to stored cell values
        |
        v
  retrieval.py        <- sentence-transformer embeddings -> top-4 examples
        |
        v
  prompt_builder.py   <- schema text + hints + examples + user question
        |
        v
  client.py           <- Groq chat completion (response cached to disk)
        |
        v
  validator.py        <- block non-SELECT / destructive SQL  [safety layer 1]
        |
        v
  executor.py         <- read-only SQLite connection          [safety layer 2]
        |
        v
  Result table + NLP analysis panel (Streamlit UI)
```

**Database:** `text2sql/data/college.db` - SQLite, 3 tables:

| Table | Columns |
|-------|---------|
| students | id, name, branch, semester, cgpa, city |
| courses  | course_id, course_name, credits, branch |
| marks    | student_id, course_id, marks, attendance |

Seed data: 60 students (ids 1 to 60), 16 courses (4 per branch), 240 marks rows (4 per student).

---

## 3. How to Set Up and Run

### Prerequisites
- Python 3.10+
- A Groq API key

### Install dependencies
```bash
pip install -r text2sql/requirements.txt
python -m spacy download en_core_web_sm
```

### Configure environment
```bash
cp text2sql/.env.example text2sql/.env
# Edit text2sql/.env and fill in:
#   GROQ_API_KEY=your_key_here
#   GROQ_MODEL=openai/gpt-oss-120b
```

### Create the database
```bash
python text2sql/db/create_db.py
```

### Run the Streamlit app (Phase 4)
```bash
streamlit run text2sql/app.py
```

### Run evaluation (Phase 5)
```bash
python text2sql/evaluation/evaluate.py
```

### Run all tests
```bash
python -m pytest -v
```

---

## 4. Current Status

**Phases 1-3 are code-complete but phase-incomplete.** The 60/60 test result is from before the Groq migration and has not been rerun against Groq. The user reports that the Groq call in `text2sql/test.py` succeeded; the app pipeline migration still needs a smoke check.
- Phase 1 (Foundation): Database seed checks, schema utilities, loaders, and 40 solved examples are recorded complete.
- Phase 2 (Baseline Pipeline): Validator, read-only executor, prompt builder, caching client, and retry are recorded complete.
- Phase 3 (NLP Modules): Modules and tests are recorded complete. Human review of schema-link scores, fuzzy-match scores/aliases, and retrieved examples remains pending. The full pipeline run and prompt review for all 15 questions also remain pending the human-authored test set.
- Confirmed project settings: `VALUE_LINK_THRESHOLD = 75`, retrieval leak-warning threshold `0.85` with exact-match failure retained, and Groq model `openai/gpt-oss-120b`. The nested `text2sql/` package layout with `llm/` and `core/` is retained.
- Next: complete the outstanding Phase 3 reviews and acceptance checks, then proceed to Phase 4 (Streamlit Web Interface with NLP Analysis panel).
See [tasks.md](tasks.md) for details.

---

## 5. Work Log

| Phase | What was built | Files created/changed | Date |
|-------|---------------|-----------------------|------|
| Setup | Tracking files | README.md, tasks.md, CHANGELOG.md, .gitignore | 2026-10-28 |
| Phase 1 | Database seed & verification, schema utilities, loaders for examples and test questions, draft 40 examples, model checker script, Phase 1 tests | `text2sql/config.py`, `text2sql/.env.example`, `text2sql/requirements.txt`, `text2sql/db/create_db.py`, `text2sql/db/schema_utils.py`, `text2sql/data/loaders.py`, `text2sql/data/examples.json`, `text2sql/check_model.py`, `text2sql/tests/test_phase1.py` | 2026-10-28 |
| Phase 2 | Safety Layer 1 (validator regex checks), Safety Layer 2 (read-only SQLite URI executor), Prompt builder (baseline & retry layouts), Client (Groq SDK, disk cache, backoff, sanitizer), Pipeline (baseline mode, self-correction retry, timing metrics), Phase 2 tests | `text2sql/core/validator.py`, `text2sql/core/executor.py`, `text2sql/llm/prompt_builder.py`, `text2sql/llm/client.py`, `text2sql/core/pipeline.py`, `text2sql/tests/test_phase2.py` | 2026-10-28 |
| Phase 3 | NLP modules: spaCy linguistic analysis, rule-based extraction (aggregates, conditions, top-N), sentence-transformer schema linking & pruning, RapidFuzz value linking with city aliases, few-shot retrieval with embedding cache and leak check, shared offline model loader, full pipeline integration, Phase 3 tests | `text2sql/nlp/preprocess.py`, `text2sql/nlp/extraction.py`, `text2sql/nlp/schema_linking.py`, `text2sql/nlp/value_linking.py`, `text2sql/nlp/retrieval.py`, `text2sql/nlp/model_utils.py`, `text2sql/nlp/pipeline_nlp.py`, `text2sql/nlp/review_phase3.py`, `text2sql/tests/test_phase3.py` | 2026-10-28 |

---

## 6. Observations

**Rule:** Record only real results copied from actual runs.
Never invent numbers, scores, or outcomes. If something was not run, say so.

| Phase | Observation | Date |
|-------|-------------|------|
| Phase 1 | SQLite DB created with 60 students, 16 courses, 240 marks rows. All Section 15 checks PASSED: Mangaluru exists in students.city, DBMS exists in courses.course_name, foreign keys valid. | 2026-10-28 |
| Phase 1 | `pytest text2sql/tests/test_phase1.py` passed 23/23 tests in 0.24s. | 2026-10-28 |
| Phase 1 | Windows console cp1252 threw UnicodeEncodeError on box-drawing characters in create_db.py; replaced with plain ASCII dashes. | 2026-10-28 |
| Phase 1 | Windows PowerShell writes UTF-8 with BOM; updated `loaders.py` to use `utf-8-sig` encoding so both BOM and standard UTF-8 parse seamlessly. | 2026-10-28 |
| Phase 1 | `courses.course_name` has 16 distinct values, exceeding the 8-value distinct threshold in SDD Section 9, so it is correctly omitted from schema text value listing. | 2026-10-28 |
| Phase 2 | Validator blocked all malicious queries: `DROP TABLE students;`, `SELECT * FROM students; DELETE FROM students;`, `UPDATE students SET cgpa = 10;`, `INSERT INTO...`, `PRAGMA...`, `ATTACH...`. | 2026-10-28 |
| Phase 2 | Validator correctly allowed queries containing protected words inside string literals (e.g. `course_name = 'Software Updates'`). | 2026-10-28 |
| Phase 2 | Read-only connection (`?mode=ro`) strictly threw `sqlite3.OperationalError: attempt to write a readonly database` when writes were attempted. | 2026-10-28 |
| Phase 2 | Baseline pipeline executed via CLI; broken query triggered exactly 1 retry (`llm_calls=2, retried=True`); zero-row query triggered 0 retries (`llm_calls=1, retried=False`); blocked query triggered 0 retries and did not execute. | 2026-10-28 |
| Phase 2 | Total test suite passed: 47 / 47 tests passed in 0.39s (`test_phase1.py` + `test_phase2.py`). | 2026-10-28 |
| Phase 3 | `analyse()` on running example returned lemmas `pupil`, `mangalore`, `dbms`, `attendance`, and noun chunks `pupils`. | 2026-10-28 |
| Phase 3 | `extract_hints()` correctly extracted `>` with value 75 from `attendance above 75%`, `>=` with value 5 from `at least 5 marks`, and `top_n = 5` from `top 5 students`. | 2026-10-28 |
| Phase 3 | Schema linking cosine similarities from `scores_log`: `pupils` -> `table students` (0.4651), `attendance` -> `marks.attendance` (0.6366), `grades` -> `table marks` (0.5851) / `students.cgpa` (0.5545), `city` -> `students.city` (0.6121), `course name` -> `courses.course_name` (0.7011). Default threshold 0.40 accepted all correct targets. | 2026-10-28 |
| Phase 3 | RapidFuzz fuzzy ratios for city variants: Mangalore/Mangaluru = 77.8, Bangalore/Bengaluru = 66.7, Mysore/Mysuru = 66.7, Shimoga/Shivamogga = 82.4, Belgaum/Belagavi = 66.7. With threshold 75, Mangalore matches directly, but Bangalore and Mysore require alias map; `CITY_ALIASES` map implemented. Short token `CSE` matched exactly; `average` and `marks` produced 0 value links. | 2026-10-28 |
| Phase 3 | Example retrieval: top-4 retrieved examples for 5 sample questions matched query semantics (similarities 0.57 to 0.91); embedding cache saved to `data/example_embeddings.npy`. | 2026-10-28 |
| Phase 3 | HuggingFace Hub network call in offline/sandbox environment triggered connection errors in 4 tests. Implemented `text2sql/nlp/model_utils.py` to load with `local_files_only=True` first, falling back to download. Confirmed 60/60 tests pass both with and without `HF_HUB_OFFLINE=1`. | 2026-10-28 |
| Phase 3 | Total test suite passed: 60 / 60 tests passed across all three phases (`test_phase1.py`, `test_phase2.py`, `test_phase3.py`) in 43.72s. | 2026-10-28 |

---

## 7. Differences from the SDD

| SDD location | SDD says | Implementation does | Reason |
|-------------|----------|---------------------|--------|
| Section 5 | Files placed directly under root `text2sql/` | Code nested inside `text2sql/` package with tracker files (`README.md`, `tasks.md`, `CHANGELOG.md`, `SDD ...pdf`) at repository root. Database at `text2sql/data/college.db`. | Kept established repository layout for clean Python package imports and root-level documentation. |
| Section 6 & 8.4 | Pure fuzzy matching on cell values with threshold | Added `CITY_ALIASES` dictionary in `value_linking.py` for colonial Kannada city names (Bangalore $\to$ Bengaluru, Mysore $\to$ Mysuru). | RapidFuzz ratios for Bangalore (66.7) and Mysore (66.7) fall below the 75 threshold. |
| Section 8.3 & 8.5 | `SentenceTransformer(EMBED_MODEL)` loaded directly | Created `text2sql/nlp/model_utils.py` shared helper `load_embedding_model()` attempting `local_files_only=True` first, falling back to download. | Avoids network check timeouts and failures when running in sandboxed or offline environments. |

---

## 8. Known Limitations

From SDD Section 17:

- Test set is only 15 questions - results show trends, not precise accuracy.
- Rule-based extraction detects that a condition exists but not always which
  column it applies to.
- Schema descriptions are hand-written for one small database.
- One database, one language (English).
- Ambiguous questions (e.g. "top students") answered with LLM best guess.
- Free LLM tiers can be slow or rate-limited; all results are cached.

---

## 9. How Someone Else Can Continue

1. Read this README fully.
2. Open `tasks.md` and find the first task marked `[ ]` (not started) or `[!]` (blocked).
3. The SDD PDF / SDD.md is the single source of truth for any design question.
4. All thresholds live only in `config.py` - never hard-code them.
5. Never read or write `data/test_questions.json` (test set must stay unseen).
6. After each phase: run Section 15 acceptance checks, paste real outputs into
   Section 6 of this README, update `tasks.md`, then stop for human
   confirmation.
7. Record every design decision and any post-evaluation change in CHANGELOG.md.
