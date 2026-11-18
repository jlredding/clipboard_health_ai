"""Staffing Q&A assistant: Claude answers questions by writing SQL against the Snowflake marts.

ask("Which state had the lowest HPRD in Q2 2024?") returns the answer plus every query it ran,
so the app can show its work.
"""
import json
import os
from functools import lru_cache

import anthropic

from db import get_schema_text, run_sql

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_QUERIES = 8  # stopping condition: the assistant can't loop forever on bad SQL

TOOLS = [
    {
        "name": "run_sql",
        "description": (
            "Run ONE read-only Snowflake SELECT (or WITH ... SELECT) query against the "
            "CLIPBOARD_HEALTH.MARTS schema. Returns column names and up to 200 rows. "
            "Write queries that aggregate in SQL rather than pulling raw rows."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sql": {"type": "string", "description": "A single Snowflake SQL SELECT statement."}
            },
            "required": ["sql"],
        },
    }
]

SYSTEM_TEMPLATE = """You are a staffing data assistant for operations leaders at a healthcare staffing company.
You answer questions about US nursing home staffing using CMS Payroll-Based Journal (PBJ) data in Snowflake.

Rules:
- Every number in your answer must come from a query result in this conversation. Never guess.
  If the data cannot answer the question, say so plainly.
- Use the run_sql tool. If you are unsure what values a column holds (for example how quarters
  are written), run a small SELECT DISTINCT first.
- HPRD (hours per resident day) is a weighted measure: total nurse hours / total resident-days.
  Never take a simple average of facility HPRDs. Use stored HPRD columns only when they are already
  at the grain you need (for example a state-quarter HPRD for a state question); for a national figure,
  sum hours and resident-days.
- Contract share = contract nurse hours / total nurse hours.
- Project conventions (these match the published dashboard and the pipeline's regression test):
  * Exclude facilities where IS_REPORTING_GAP is TRUE (they report almost no hours) from every
    national, state, and percentage figure, unless the user asks to include them. Say in one short
    clause that reporting-gap facilities were excluded. MART_STATE_QUARTER already excludes them.
  * "Below 3.0 HPRD" means BELOW_REFERENCE is TRUE in MART_FACILITY_QUARTER.
  * A "watchlist" facility has 10 or more days below the low-staffing threshold in a quarter
    (DAYS_BELOW_LOW_THRESHOLD >= 10); MART_STATE_QUARTER.WATCHLIST_FACILITIES counts them by state.
  * Quarters are written like '2024Q2'.
  * Round in SQL, not in your head: wrap reported values in ROUND(x, 2) for HPRD and
    ROUND(x * 100, 1) for percentages, so your figures match the dashboard exactly.
- Lead with the answer, then one or two sentences of context. Round HPRD to 2 decimals and
  percentages to 1 decimal. Name the table(s) and quarter(s) you used.

Database CLIPBOARD_HEALTH, schema MARTS. Tables and columns:
{schema}
"""


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return SYSTEM_TEMPLATE.format(schema=get_schema_text())


def ask(question: str, history: list | None = None) -> dict:
    """Answer one question. Returns {"answer", "queries", "messages"}.

    queries: list of {"sql", "row_count"} or {"sql", "error"} in the order they ran.
    messages: the full conversation, so a chat UI can pass it back as history for follow-ups.
    """
    client = anthropic.Anthropic()
    messages = list(history or []) + [{"role": "user", "content": question}]
    queries: list[dict] = []

    for _turn in range(MAX_QUERIES + 2):  # hard stop even if the model keeps asking for tools
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=system_prompt(),
            tools=TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            answer = "".join(b.text for b in resp.content if b.type == "text").strip()
            return {"answer": answer, "queries": queries, "messages": messages}

        results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            sql = block.input.get("sql", "")
            if len(queries) >= MAX_QUERIES:
                content, is_error = "Query limit reached. Answer with what you have, or say you couldn't.", True
            else:
                try:
                    result = run_sql(sql)
                    queries.append({"sql": result["sql"], "row_count": result["row_count"]})
                    content, is_error = json.dumps(result), False
                except Exception as e:  # bad SQL, blocked query, timeout: the model sees the error and can fix it
                    queries.append({"sql": sql, "error": str(e)})
                    content, is_error = f"Error: {e}", True
            results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error}
            )
        messages.append({"role": "user", "content": results})

    return {
        "answer": "I couldn't reach an answer within the query limit. Try a narrower question.",
        "queries": queries,
        "messages": messages,
    }
