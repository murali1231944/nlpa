# CHANGELOG -- NLP-Powered Text-to-SQL Interface

This file records every design decision and any change made after seeing
evaluation results. It exists so the project report can state honestly what
was changed and why.

Format per entry: Date | Phase | What changed | Why

---

## 2026-10-28 -- Setup

- Created README.md, tasks.md, CHANGELOG.md as initial tracking files.
  No code written yet. No deviations from the SDD.

---

## 2026-10-28 -- Phase 1

### Decision: gold_values JSON shape
- SDD Section 7.4 says gold_values is "list of pairs of column and stored
  value" but does not fix the JSON shape.
- Chosen shape: each item is {"column": "table.col", "value": "stored_value"}
- Reason: object form is self-documenting and unambiguous. Confirmed by the
  human in the Phase 1 briefing.

### Decision: examples.json field names
- SDD Section 7.3 lists the fields. Confirmed by human: id (int), question
  (str), sql (str), tags (list of str from allowed set).
- The loader validates against these fields exactly.

### Decision: utf-8-sig encoding in loaders
- PowerShell Set-Content writes UTF-8 with BOM by default on Windows.
- json.load() with encoding="utf-8" fails on BOM files.
- Fix: open files with encoding="utf-8-sig" which transparently strips BOM
  and also handles plain UTF-8. Applies to both loaders.
- This is a Windows-specific workaround, not a deviation from the SDD.

### Decision: GEMINI_MODEL default in .env.example
- Set to gemini-2.5-flash as specified in SDD Section 3.
- SDD note: "gemini-1.5 models have been shut down" -- confirmed by human.
- The check_model.py script lists available models and stops if the
  configured model is not found. It never switches models silently.

### Observation: Unicode print error on Windows
- create_db.py used Unicode box-drawing characters (U+2500) in print().
- Windows cp1252 console raises UnicodeEncodeError on these characters.
- Fix: replaced with plain ASCII dashes. Not a deviation from SDD.

### Observation: course_name not in schema text value listing
- courses.course_name has 16 distinct values, which exceeds the 8-value
  threshold in SDD Section 9. So course names are NOT listed in the schema
  text. This is correct per the SDD rule.

---

## 2026-10-28 -- Phase 2

### Decision: Module placement in core/ and llm/
- Followed SDD Section 5 layout:
  `llm/prompt_builder.py`, `llm/client.py`, `core/validator.py`, `core/executor.py`, `core/pipeline.py`.
- tasks.md listed `pipeline/client.py` as shorthand, but SDD layout is the single source of truth.

### Decision: SQLite URI for read-only connection on Windows
- Windows file paths with backslashes require valid URI encoding.
- Used `Path(DB_PATH).resolve().as_uri() + "?mode=ro"` with `sqlite3.connect(uri, uri=True)`.
- Verified on Windows: reads succeed, attempted writes raise `sqlite3.OperationalError: attempt to write a readonly database`.

### Decision: String literal blanking in validator
- Regex replaces `'...'` (including `''` escapes) and `"..."` with empty quotes before scanning keywords.
- This ensures queries filtering on words like "update" (e.g. `'Software Updates'`) or "delete" are not blocked.

### Observation: Schema column names
- Primary key in `students` is named `id`, whereas foreign key in `marks` is `student_id`.
- Test queries updated to reference `students.id`.

---

## 2026-10-28 -- Phase 3

### Decision: Embedding model for schema linking
- SDD §8.3 specified schema descriptions embedded once at import with EMBED_MODEL (`all-MiniLM-L6-v2`) and cosine via normalized dot product.
- Real scores produced on candidate phrases:
  - `pupils` -> `table students` (score: 0.4651) [ACCEPTED >= 0.40]
  - `attendance` -> `marks.attendance` (score: 0.6366) [ACCEPTED >= 0.40]
  - `grades` -> `table marks` (score: 0.5851) [ACCEPTED >= 0.40]
  - `course name` -> `courses.course_name` (score: 0.7011) [ACCEPTED >= 0.40]
  - `cgpa` -> `students.cgpa` (score: 0.5546) [ACCEPTED >= 0.40]
  - `city` -> `students.city` (score: 0.6121) [ACCEPTED >= 0.40]

### Decision: RapidFuzz scores & Alias Map for Colonial City Names
- RapidFuzz `fuzz.ratio` on historical vs current Kannada city names:
  - `Mangalore` vs `Mangaluru`: 77.8
  - `Bangalore` vs `Bengaluru`: 66.7
  - `Mysore` vs `Mysuru`: 66.7
  - `Shimoga` vs `Shivamogga`: 82.4
  - `Belgaum` vs `Belagavi`: 66.7
- With default threshold = 80, Mangalore (77.8), Bangalore (66.7), and Mysore (66.7) fall below 80.
- Implemented `CITY_ALIASES` map in `value_linking.py` to resolve colonial names directly to modern stored values, while preserving RapidFuzz for typological and spelling variations.

### Decision: Short-token guard (< 4 characters)
- Short acronyms (e.g. `CSE`, `ISE`) require exact case-insensitive equality to avoid false fuzzy matches on small substrings (e.g. `cs` does not link to `CSE`).

### Decision: Schema Pruning with Bridge Table
- Implemented pruning logic in `schema_linking.py` and `schema_utils.py`:
  - When `students` and `courses` are present, `marks` is automatically added as the bridge table.
  - When no tables match, falls back to all tables.

### Decision: VALUE_LINK_THRESHOLD = 75
- Confirmed by human: the SDD copy was an older export and replaced by SDD.md.
- Default `VALUE_LINK_THRESHOLD = 75` in `config.py` is maintained.

### Decision: Repository Layout Deviation
- SDD Section 5 shows flat layout under root `text2sql/`.
- Implementation retains established Python package structure: `text2sql/` subpackage with `data/college.db` inside it, and tracker files (`README.md`, `tasks.md`, `CHANGELOG.md`, `.gitignore`) at the repository root.
- Confirmed by human and recorded as an architectural layout deviation.

### Decision: Shared Offline-First Embedding Model Loader (`model_utils.py`)
- Direct calls to `SentenceTransformer(EMBED_MODEL)` triggered Hugging Face Hub metadata network checks, throwing `[Errno 11001] getaddrinfo failed` and failing 4 tests in sandboxed/offline environments.
- Created `text2sql/nlp/model_utils.py` with `load_embedding_model()`, which attempts `local_files_only=True` first and falls back to standard download if un-cached.
- Shared across both `schema_linking.py` and `retrieval.py`.
- Verified: Test suite achieves 60/60 PASS both with and without `HF_HUB_OFFLINE=1`.

### Decision: GEMINI_MODEL set to gemini-3.8-flash
- Running `check_model.py` with `gemini-2.5-flash` returned `404 NOT_FOUND: This model models/gemini-2.5-flash is no longer available to new users. Please update your code to use models/gemini-3.8-flash`.
- Per human instruction and approval, updated `GEMINI_MODEL=gemini-3.8-flash` in `text2sql/.env`.

### Decision: Retrieval Leak-Warning Threshold Lowered to 0.85
- SDD §8.5 specified raising an error on exact match and printing a warning at similarity > 0.95.
- Lowered similarity warning threshold from 0.95 to 0.85 in `nlp/retrieval.py`.
- Preserved exact-match failure (`ValueError: DATA LEAK DETECTED`).
- `check_and_report_leakage()` returns each test question's highest similarity and target example for reporting.

---

*(Add entries here as work progresses. Never delete old entries.)*

## 2026-10-28 -- Human-confirmed documentation reconciliation

- Confirmed `VALUE_LINK_THRESHOLD = 75`; retain the RapidFuzz city alias map for human review.
- Confirmed retrieval leak-warning threshold `0.85`; retain the exact-match failure check.
- At the time of this entry, `GEMINI_MODEL=gemini-3.8-flash` was the configured project model; this was superseded by the later Groq migration entry.
- Confirmed the nested `text2sql/` package layout, including `llm/` and `core/`.
- Clarified that Phases 1-3 are code-complete but phase-incomplete. Phase 3 human reviews and acceptance checks remain pending.
- Read-only structural inspection found `text2sql/data/examples.json` present with 40 items and the expected fields. No example data was changed; `test_questions.json` was not inspected.

## 2026-10-28 -- LLM provider migration to Groq

- Per user request, migrated the application LLM client from Google GenAI to Groq chat completions.
- Use `GROQ_API_KEY` and `GROQ_MODEL`; default model is `openai/gpt-oss-120b`, matching the user's reported successful Groq `test.py` setup.
- Replaced the Google SDK dependency and updated the model-check utility, `.env.example`, README, and task tracker.
- The SDD still specifies Gemini; this provider change is a documented deviation.
- The Groq application client has not yet been independently smoke-checked; no API call was made during this migration.


