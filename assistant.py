"""Staffing Q&A assistant: Claude answers questions with two tools.

  run_sql      read-only SQL against the Snowflake marts (numbers)
  search_docs  search over CMS PBJ documentation and the project glossary (definitions, rules)

ask("Which state had the lowest HPRD in Q2 2024?") returns the answer, every query it ran, and
every document passage it cited, so the app can show its work.
"""
import json
import os
import re
from functools import lru_cache

import anthropic

from db import get_schema_text, run_sql
from rag import search

MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
MAX_TOOL_CALLS = 10  # stopping condition: the assistant can't loop forever

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
    },
    {
        "name": "search_docs",
        "description": (
            "Search CMS Payroll-Based Journal documentation (public use file specifications, data "
            "dictionaries, the PBJ policy manual) and the project's metric glossary. Use it for "
            "definitions, data rules, exclusions, column meanings and 'why' questions. Returns "
            "passages with an id like C12; cite the ids you use."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "What to look up, in plain words."}},
            "required": ["query"],
        },
    },
]

SYSTEM_TEMPLATE = """You are a staffing data assistant for operations leaders at a healthcare staffing company.
You answer questions about US nursing home staffing using CMS Payroll-Based Journal (PBJ) data in Snowflake
and CMS documentation.

Rules:
- Every number in your answer must come from a query result in this conversation, and every definition
  or rule must come from a search_docs passage. Never answer from memory. If the data or documents
  cannot answer the question, say so plainly.
- Numbers: use run_sql. If you are unsure what values a column holds, run a small SELECT DISTINCT first.
- Definitions, rules, exclusions, "what does X mean", "why": use search_docs. Cite each passage you rely
  on with its id in square brackets right after the claim, like [C4]. Only cite ids that search_docs returned.
- You are read-only. If asked to change, delete or load data, say you can't and don't try.
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
- Lead with the answer, then one or two sentences of context. Name the table(s) and quarter(s) you used.

Database CLIPBOARD_HEALTH, schema MARTS. Tables and columns:
{schema}
"""


@lru_cache(maxsize=1)
def system_prompt() -> str:
    return SYSTEM_TEMPLATE.format(schema=get_schema_text())


def search_docs(query: str, k: int = 5) -> list[dict]:
    """search() results trimmed to what the model needs."""
    return [
        {"id": r["id"], "source": r["source"], "location": r["location"], "text": r["text"]}
        for r in search(query, k)
    ]


def run_tool(name: str, args: dict, log: dict) -> tuple[str, bool]:
    """Execute one tool call. Records it in log["queries"] or log["passages"]. Returns (content, is_error)."""
    if name == "run_sql":
        sql = args.get("sql", "")
        try:
            result = run_sql(sql)
            log["queries"].append({"sql": result["sql"], "row_count": result["row_count"]})
            return json.dumps(result), False
        except Exception as e:  # bad SQL, blocked query, timeout: the model sees the error and can fix it
            log["queries"].append({"sql": sql, "error": str(e)})
            return f"Error: {e}", True
    if name == "search_docs":
        passages = search_docs(args.get("query", ""))
        for p in passages:
            log["passages"].setdefault(p["id"], p)
        return json.dumps(passages), False
    return f"Error: unknown tool {name}", True


def cited_sources(answer: str, passages: dict) -> list[dict]:
    """The passages the answer actually cites, in order of first citation."""
    seen = []
    for pid in re.findall(r"\[(C\d+)\]", answer):
        if pid in passages and pid not in seen:
            seen.append(pid)
    return [passages[p] for p in seen]


def ask(question: str, history: list | None = None) -> dict:
    """Answer one question.

    Returns {"answer", "queries", "sources", "messages", "usage"}:
      queries: SQL run, in order ({"sql", "row_count"} or {"sql", "error"})
      sources: document passages cited in the answer
      messages: the full conversation, to pass back as history for follow-ups
      usage: input/output tokens for this question
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    messages = list(history or []) + [{"role": "user", "content": question}]
    log = {"queries": [], "passages": {}}
    usage = {"input_tokens": 0, "output_tokens": 0}
    calls = 0

    def result(answer: str) -> dict:
        return {
            "answer": answer,
            "queries": log["queries"],
            "sources": cited_sources(answer, log["passages"]),
            "messages": messages,
            "usage": usage,
        }

    for _turn in range(MAX_TOOL_CALLS + 2):  # hard stop even if the model keeps asking for tools
        resp = client.messages.create(
            model=MODEL,
            max_tokens=1500,
            system=system_prompt(),
            tools=TOOLS,
            messages=messages,
        )
        usage["input_tokens"] += resp.usage.input_tokens
        usage["output_tokens"] += resp.usage.output_tokens
        messages.append({"role": "assistant", "content": resp.content})

        if resp.stop_reason != "tool_use":
            return result("".join(b.text for b in resp.content if b.type == "text").strip())

        tool_results = []
        for block in resp.content:
            if block.type != "tool_use":
                continue
            calls += 1
            if calls > MAX_TOOL_CALLS:
                content, is_error = "Tool limit reached. Answer with what you have, or say you couldn't.", True
            else:
                content, is_error = run_tool(block.name, block.input, log)
            tool_results.append(
                {"type": "tool_result", "tool_use_id": block.id, "content": content, "is_error": is_error}
            )
        messages.append({"role": "user", "content": tool_results})

    return result("I couldn't reach an answer within the tool limit. Try a narrower question.")
