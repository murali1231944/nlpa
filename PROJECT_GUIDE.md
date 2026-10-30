# Text-to-SQL Project Guide

This guide explains the project in simple terms. It is written so a classmate can understand the idea and follow the demo without needing the source code open.

## 1. What does the project do?

The project lets a person ask a question about college data in ordinary English. The app prepares the question and useful database information, asks Groq to write a SQL query, safely runs that query on a local SQLite database, and shows the answer.

For example, a person can ask:

> Show the average marks for pupils from Mangalore in DBMS with attendance above 75%.

The person does not need to know SQL. The app turns the question into a query the database can run.

## 2. High-level design

```text
Person
  |
  v
Streamlit screen (app.py)
  |
  v
Question processing (NLP modules, full mode)
  |  words and clues
  |  likely tables, columns, and stored values
  |  similar solved examples
  v
Prompt builder: question + selected schema + useful context
  |
  v
Groq: writes SQL
  |
  v
Safety check: allow only a safe SELECT query
  |
  v
SQLite database: runs the query read-only
  |
  v
Streamlit screen: shows SQL and returned rows
```

The project has two modes:

- **Full mode** runs the NLP preparation steps and adds their findings to the prompt.
- **Baseline mode** is a simpler comparison path. It uses the question and the database schema without the full NLP preparation and retrieved examples.

The goal of selecting relevant schema is to keep the prompt focused and potentially use fewer tokens than sending every table. Token savings have not been measured, so present this as a design goal rather than a proven result.

## 3. NLP steps, using one example

Example question:

> Show the average marks for pupils from Mangalore in DBMS with attendance above 75%.

The steps below describe what each part is for. The exact matches can vary with the question and model results.

### Step 1 — Split and study the words

**Module:** `text2sql/nlp/preprocess.py`

The app splits the sentence into tokens, finds word roots (lemmas), identifies parts of speech, and collects noun phrases.

For example, it can recognize `pupils` as a noun phrase and reduce word forms to simpler roots. This is useful because people may use different forms of a word when referring to the same idea.

**NLP concepts:**

- **Tokenization:** splitting a sentence into words and punctuation.
- **Lemmatization:** changing a word to its dictionary form, such as “students” to “student.”
- **Part-of-speech tagging:** labeling words as nouns, verbs, adjectives, and so on.
- **Noun-phrase extraction:** finding word groups that name people, places, subjects, or things.

The current pipeline uses the noun phrases and lemmas as candidates for schema matching. It also produces part-of-speech tags for inspection in the demo.

### Step 2 — Find clues about the requested data

**Module:** `text2sql/nlp/extraction.py`

The app looks for familiar phrases that suggest a database operation. In this example, `average` suggests AVG, and `above 75%` suggests a greater-than condition with the number 75.

**NLP concept:** rule-based information extraction. The module uses written word patterns to detect aggregate requests, comparison operators with numbers, and top-N requests such as “top 5.”

These are clues for Groq, not a complete understanding of the sentence. In particular, the module finds an operator and number; it does not always know which database column that condition belongs to.

### Step 3 — Match words to database tables and columns

**Module:** `text2sql/nlp/schema_linking.py`

The question says `pupils`, while the database table is called `students`. The app compares the meaning of question phrases with descriptions of database tables and columns, then keeps likely matches. It uses the `all-MiniLM-L6-v2` sentence-embedding model and cosine similarity scores. The configured acceptance threshold is 0.40.

**NLP concepts:**

- **Sentence embeddings:** representing words or phrases as number lists that capture some of their meaning.
- **Semantic similarity:** comparing those number lists to find phrases with related meanings, even when the spelling differs.
- **Schema linking:** connecting a phrase in the question to a database table or column.

For this question, useful targets may include `students`, `marks`, `courses`, and columns such as `marks.attendance` or `marks.marks`. The app also keeps `marks` when needed to connect students to courses.

### Step 4 — Match names to values stored in the database

**Module:** `text2sql/nlp/value_linking.py`

The database stores the city as `Mangaluru`, while the question says `Mangalore`. The app uses a small alias list for known city-name variants and RapidFuzz string similarity for other spelling variations. A match must meet the configured score threshold of 75. Very short words must match exactly to avoid mistaken matches.

**NLP concept:** fuzzy string matching. It compares spellings that are close but not identical. The alias list handles known names that are too different for the fuzzy threshold.

This helps the prompt tell Groq to use the exact value that exists in SQLite.

### Step 5 — Find similar solved examples

**Module:** `text2sql/nlp/retrieval.py`

The app compares the new question with the project’s solved question-and-SQL examples and retrieves up to four similar ones.

**NLP concept:** semantic search using sentence embeddings. It looks for examples with similar meaning, not only identical words. These examples can show Groq the database’s query style.

### Step 6 — Prepare the prompt for Groq

**Module:** `text2sql/llm/prompt_builder.py`

The prompt contains the original question, the selected database schema, the extracted clues, matched values, and retrieved examples. It also tells Groq to return one SELECT query and use the listed schema.

This is where the NLP preparation helps focus the information sent to the language model. Groq is still the part that writes the SQL.

### Step 7 — Check and run the SQL

**Modules:** `text2sql/core/validator.py`, `text2sql/core/executor.py`

Before running the query, the app checks that it is a single SELECT statement and rejects dangerous SQL commands. It then runs the query through a read-only SQLite connection. If SQLite reports a query error, the pipeline can ask Groq for one correction attempt.

This part is database safety and execution, rather than NLP.

### Step 8 — Show the answer

**Module:** `text2sql/app.py`

The Streamlit screen shows the generated SQL and the rows returned by SQLite. In full mode, it also shows the processing steps so the presenter can explain how the question was prepared.

## 4. Main technologies

| Technology | What it does here |
|---|---|
| Python | Runs the application and connects its modules. |
| Streamlit | Displays the question form, processing details, SQL, and results. |
| spaCy | Tokenizes and analyzes words, lemmas, parts of speech, and noun phrases. |
| Sentence Transformers | Finds semantically related schema descriptions and solved examples. |
| RapidFuzz | Finds database values with similar spellings. |
| Groq | Generates SQL from the prompt prepared by the project. The configured default model is `openai/gpt-oss-120b`; the model setting can be overridden through the environment. |
| SQLite | Stores college data and executes the generated query. |
| pytest | Holds automated checks for the project modules. |

The configured Groq model is read from project configuration/environment settings. Do not put API keys in this guide, slides, screenshots, or source code.

## 5. Database in this project

The local database file is `text2sql/data/college.db`. The documented tables are:

| Table | Example information |
|---|---|
| `students` | Student name, branch, semester, CGPA, and city. |
| `courses` | Course name, credits, and branch. |
| `marks` | Student/course connection, marks, and attendance. |

The `marks` table connects students to courses. That is why a question about students in a course may need all three tables.

## 6. Folder and file guide

```text
NLP/
|-- README.md                 Main setup and project summary
|-- PROJECT_GUIDE.md          This plain-language design and presentation guide
|-- CHANGELOG.md              Recorded decisions and changes
|-- tasks.md                  Work tracker and pending acceptance checks
|-- SDD NLP-Powered Text-to-SQL Interface.pdf
|                              Original software design document
|-- text2sql/
    |-- app.py                Streamlit user interface
    |-- config.py             Paths, model settings, and thresholds
    |-- requirements.txt      Python packages needed by the project
    |-- check_model.py        Utility for checking a model setup
    |-- test.py               Separate model/API test script
    |-- core/
    |   |-- pipeline.py       Connects question, prompt, model, safety, and database steps
    |   |-- validator.py       Rejects unsafe SQL
    |   |-- executor.py        Runs allowed SQL read-only
    |-- nlp/
    |   |-- preprocess.py     Word and phrase analysis
    |   |-- extraction.py     Aggregate, comparison, number, and top-N clues
    |   |-- schema_linking.py  Matches question phrases to tables and columns
    |   |-- value_linking.py   Matches question phrases to stored database values
    |   |-- retrieval.py       Finds similar solved examples
    |   |-- model_utils.py    Loads the embedding model for NLP tasks
    |   |-- pipeline_nlp.py   Runs the Phase 3 NLP modules in order
    |-- llm/
    |   |-- prompt_builder.py Builds the model prompt
    |   |-- client.py         Calls Groq and caches generated SQL
    |-- db/
    |   |-- create_db.py      Creates/seeds the SQLite database
    |   |-- schema_utils.py   Reads and formats the database schema
    |-- data/
    |   |-- college.db       Local SQLite database
    |   |-- examples.json    Solved question-and-SQL examples for retrieval
    |   |-- example_embeddings.npy
    |   |                    Cached vectors used for example search
    |   |-- llm_cache.json   Cached model responses
    |-- evaluation/           Evaluation package; evaluation runner is pending
    |-- tests/                Automated module checks
```

The folders are grouped by responsibility: `nlp/` understands and prepares the question, `llm/` prepares and sends the model prompt, `core/` controls the overall pipeline and SQL safety, `db/` handles schema/database setup, `data/` contains the database and supporting data, and `tests/` contains automated checks.

Evaluation results are intended to be saved under the configured `text2sql/data/results/` path when Phase 5 is implemented; that output folder is not shown as an existing folder above.

## 7. What to say during a demo

> “The user asks a database question in plain English. Our NLP steps break down the words, find clues like averages and number limits, match the wording to the database tables and stored values, and find similar solved examples. The app gives that context to Groq, which writes SQL. The app checks the SQL, runs it read-only on SQLite, and shows the results.”

If asked why not send the whole schema directly to Groq:

> “That is possible. Our full pipeline tries to select the schema and examples relevant to the question, so the prompt is more focused. We have not yet measured token savings or overall accuracy, so we describe those as goals until evaluation is complete.”

## 8. Current project status and limits

The task tracker records Phases 1–3 as **code-complete but phase-incomplete**: human reviews and acceptance checks remain pending. The Streamlit interface is available for a demo, but its Phase 4 acceptance checklist is still tracked separately. The evaluation scripts and outputs are listed as pending work in the task tracker; do not present evaluation as complete until the required files and results exist.

The system is designed around one small English-language college database. NLP matching can select the wrong table or value, and Groq can generate incorrect SQL. A working example demonstrates the flow, but it does not prove accuracy across many questions. The project’s 45–60 second response time has been reported during a live use; it has not been broken down into measured stage timings in this guide.
