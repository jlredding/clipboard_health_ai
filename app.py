"""Streamlit chat app for the staffing assistant.

  streamlit run app.py

Locally it reads .env. On Streamlit Community Cloud, put the same keys in the app's Secrets
(SNOWFLAKE_PRIVATE_KEY holds the key text instead of SNOWFLAKE_PRIVATE_KEY_PATH).
"""
import os

import streamlit as st

# Streamlit Cloud secrets -> environment variables, before importing modules that read them.
try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except Exception:  # no secrets file locally: .env is used instead
    pass

from assistant import ask, system_prompt  # noqa: E402
from rag import search  # noqa: E402

MAX_QUESTIONS = int(os.environ.get("MAX_QUESTIONS_PER_SESSION", "15"))  # protects the API budget
EXAMPLES = [
    "Which state had the lowest HPRD in Q2 2026?",
    "Which Texas facilities over 100 beds were below 3.0 HPRD in Q2 2026?",
    "How has the national contract share changed since Q2 2024?",
    "What counts as contract staff, and why are reporting-gap facilities excluded?",
    "Which nursing homes does CMS leave out of the PBJ public use files?",
]

st.set_page_config(page_title="Nursing Home Staffing Assistant", page_icon="🩺", layout="wide")


@st.cache_resource(show_spinner="Connecting to Snowflake and loading the document index...")
def warm_up() -> bool:
    system_prompt()          # reads the MARTS schema from Snowflake
    search("warm up", k=1)   # loads the embedding model and index
    return True


def check_password() -> bool:
    required = os.environ.get("APP_PASSWORD")
    if not required or st.session_state.get("authed"):
        return True
    pw = st.text_input("This demo uses a paid API. Enter the access code:", type="password")
    if pw and pw == required:
        st.session_state.authed = True
        st.rerun()
    elif pw:
        st.error("That code didn't work.")
    return False


def render_turn(turn: dict) -> None:
    with st.chat_message("assistant"):
        st.markdown(turn["answer"])
        if turn["queries"]:
            with st.expander(f"SQL run ({len(turn['queries'])})"):
                for i, q in enumerate(turn["queries"], 1):
                    label = f"Query {i}: " + (f"error: {q['error']}" if "error" in q else f"{q['row_count']} rows")
                    st.caption(label)
                    st.code(q["sql"], language="sql")
        if turn["sources"]:
            with st.expander(f"Sources ({len(turn['sources'])})"):
                for s in turn["sources"]:
                    st.markdown(f"**[{s['id']}] {s['source']}**, {s['location']}")
                    st.caption(s["text"][:600] + ("..." if len(s["text"]) > 600 else ""))


# ---------- page ----------
st.title("Nursing Home Staffing Assistant")
st.caption(
    "Ask about US nursing home staffing (CMS Payroll-Based Journal, Q2 2024 and Q3 2025 to Q2 2026). "
    "Answers come from SQL on Snowflake and from CMS documentation, and show their work."
)

with st.sidebar:
    st.subheader("Try asking")
    for ex in EXAMPLES:
        if st.button(ex, use_container_width=True):
            st.session_state.pending = ex
    st.divider()
    st.subheader("How it works")
    st.markdown(
        "- **run_sql**: Claude writes SQL against the pipeline's dbt marts as a read-only Snowflake user "
        "(SELECT only, 30 s timeout, 200-row cap)\n"
        "- **search_docs**: hybrid search (embeddings + BM25) over CMS PBJ documentation and the project "
        "glossary; answers cite the passage\n"
        "- Evaluated on 18 questions with known answers"
    )
    st.markdown(
        "[Pipeline](https://github.com/jlredding/clipboard_health_pipeline) · "
        "[Assistant code](https://github.com/jlredding/clipboard_health_ai) · "
        "[Dashboard](https://clipboard-health-staffing.streamlit.app/)"
    )
    if st.button("New conversation"):
        st.session_state.history, st.session_state.turns = None, []
        st.rerun()

if not check_password():
    st.stop()

warm_up()
st.session_state.setdefault("history", None)
st.session_state.setdefault("turns", [])

for turn in st.session_state.turns:
    with st.chat_message("user"):
        st.markdown(turn["question"])
    render_turn(turn)

question = st.chat_input("Ask a staffing question") or st.session_state.pop("pending", None)
if question:
    if len(st.session_state.turns) >= MAX_QUESTIONS:
        st.warning(f"This demo allows {MAX_QUESTIONS} questions per session. Refresh the page to start over.")
        st.stop()
    with st.chat_message("user"):
        st.markdown(question)
    with st.spinner("Querying Snowflake and the docs..."):
        try:
            result = ask(question, st.session_state.history)
        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.stop()
    turn = {"question": question, **result}
    st.session_state.history = result["messages"]
    st.session_state.turns.append(turn)
    render_turn(turn)
