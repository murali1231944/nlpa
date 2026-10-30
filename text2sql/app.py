"""Streamlit interface for the NLP-powered Text-to-SQL project."""

import pandas as pd
import streamlit as st

from text2sql.core.pipeline import answer
from text2sql.data.loaders import load_examples
from text2sql.db.schema_utils import get_schema_text


st.set_page_config(
    page_title="Text-to-SQL | College Database",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="expanded",
)


def choose_example() -> None:
    """Copy the selected solved example question into the input box."""
    selected = st.session_state.get("selected_example")
    if selected:
        st.session_state.question = selected


st.title("NLP-Powered Text-to-SQL")
st.write("Ask a question about the college database in plain English.")

with st.sidebar:
    st.markdown("### Explore the database")
    st.caption("See the available tables and try a solved example.")
    try:
        with st.expander("Database schema", expanded=False):
            st.code(get_schema_text(), language="text")
    except Exception:
        st.warning("The database schema could not be loaded.")

    st.divider()
    st.markdown("### Example questions")
    try:
        examples = load_examples()
        example_questions = [item["question"] for item in examples]
        st.selectbox(
            "Choose a question to try",
            [""] + example_questions,
            key="selected_example",
            label_visibility="collapsed",
        )
        st.button("Use this question", on_click=choose_example, width="stretch")
    except Exception:
        st.info("Example questions are unavailable.")

st.subheader("Ask a question")
question = st.text_area(
    "Question",
    key="question",
    placeholder="For example: Show the top 5 students in DBMS from Mangalore",
    height=100,
    label_visibility="collapsed",
)

mode_col, action_col = st.columns([3, 1], vertical_alignment="bottom")
with mode_col:
    mode = st.radio(
        "Choose how to process the question",
        ["full", "baseline"],
        format_func=lambda value: "Full NLP pipeline" if value == "full" else "Baseline",
        horizontal=True,
        help="Full mode shows the NLP analysis. Baseline sends the question through the simpler path.",
    )
with action_col:
    ask_clicked = st.button("Generate answer", type="primary", disabled=not question.strip(), width="stretch")

if ask_clicked:
    try:
        with st.spinner("Analyzing the question and generating SQL. A live model call can take up to about 90 seconds."):
            st.session_state.text2sql_result = answer(question.strip(), mode=mode)
            st.session_state.text2sql_mode = mode
            st.session_state.text2sql_question = question.strip()
    except Exception as exc:
        st.session_state.text2sql_result = None
        st.error(f"The request failed: {exc}")

result = st.session_state.get("text2sql_result")
if st.session_state.get("text2sql_question") != question.strip():
    result = None
if result:
    st.divider()
    nlp = result.get("nlp") or {}

    st.subheader("How the question is processed")
    st.caption("Follow the question from the original words to the database answer.")
    if st.session_state.get("text2sql_mode") == "full":
        analysis = nlp.get("analysis") or {}

        st.markdown("### Step 1 — Analyze the words")
        st.write("The app splits the question into tokens, finds word roots, and identifies noun phrases.")
        st.markdown("**Tokens**")
        st.write(analysis.get("tokens", []))
        st.markdown("**Lemmas (word roots)**")
        st.write(analysis.get("lemmas", []))
        st.markdown("**Noun phrases**")
        st.write(analysis.get("noun_chunks", []))

        st.markdown("### Step 2 — Find SQL clues")
        st.write("The app looks for requests such as averages, comparisons, and top-N limits.")
        st.json(nlp.get("hints") or {})

        st.markdown("### Step 3 — Find relevant tables and columns")
        st.write("The app matches words in the question to parts of the database schema.")
        st.json(nlp.get("schema_links") or {})
        if nlp.get("scores_log"):
            with st.expander("See candidate match scores"):
                st.json(nlp["scores_log"])
        st.markdown("**Tables selected for the query**")
        st.write(nlp.get("pruned_tables") or [])

        st.markdown("### Step 4 — Match database values")
        st.write("The app connects names in the question to values stored in the database, such as a city name or course.")
        st.json(nlp.get("value_links") or [])

        st.markdown("### Step 5 — Find similar examples and prepare the prompt")
        st.write("The app retrieves similar question-and-SQL examples, then combines them with the question and selected schema for Groq.")
        st.json(nlp.get("retrieved_examples") or [])
        with st.expander("See the prompt sent to Groq"):
            st.code(result.get("prompt", ""), language="text")
    else:
        st.info("Baseline mode skips the detailed NLP steps and uses the simpler question-to-SQL path.")

    st.markdown("### Step 6 — Generate the SQL")
    st.write("Groq uses the prepared prompt to produce a SQL query.")
    if result.get("sql"):
        st.code(result["sql"], language="sql")
    else:
        st.info("No SQL query was produced.")

    st.markdown("### Step 7 — Run the query")
    st.write("The app runs the generated SQL on the college database and displays the returned rows.")
    error = result.get("error")
    if error:
        if str(error).startswith("Blocked by safety validator"):
            st.warning(error)
        else:
            st.error(error)
    else:
        if result.get("retried"):
            st.info("The SQL needed one correction attempt before it ran.")
        rows = result.get("rows", [])
        columns = result.get("columns", [])
        if rows:
            st.dataframe(pd.DataFrame(rows, columns=columns), width="stretch", hide_index=True)
        else:
            st.info("The query ran but returned no rows.")

    if (nlp.get("analysis") or {}).get("pos"):
        with st.expander("Optional detail: part-of-speech tags"):
            st.json(nlp["analysis"]["pos"])
