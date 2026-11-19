"""Staffing monitor agent: runs after each pipeline load and reports what changed.

  python3 monitor.py                    # latest quarter; writes reports/, no GitHub issues
  python3 monitor.py --quarter 2026Q2   # a specific quarter
  python3 monitor.py --open-issues      # also open GitHub issues for high-severity findings
                                        # (needs GITHUB_TOKEN and GITHUB_REPOSITORY, e.g. in Actions)

How it works (plan -> act -> check):
  1. Detect (plain SQL, no LLM): facilities and states whose HPRD, contract share or watchlist
     count moved past fixed thresholds since their previous loaded quarter.
  2. Investigate (Claude with tools): run_sql, get_facility_profile, compare_quarters, search_docs.
     Claude decides whether each signal is a real staffing change or a reporting artifact.
  3. Record: every finding must cite query ids from THIS run as evidence, or it is rejected.
  4. Act: write a markdown staffing brief; open a GitHub issue only for high-severity findings,
     and only with --open-issues. The agent never changes data (read-only Snowflake role).

Guardrails: read-only role, max tool calls, token budget, evidence check, full trace log (JSONL).
"""
import argparse
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic

from assistant import MODEL, search_docs
from db import get_schema_text, run_sql

MONITOR_MODEL = os.environ.get("MONITOR_MODEL", MODEL)
MAX_TOOL_CALLS = int(os.environ.get("MONITOR_MAX_TOOL_CALLS", "40"))
TOKEN_BUDGET = int(os.environ.get("MONITOR_TOKEN_BUDGET", "800000"))  # input + output, whole run
MAX_OUTPUT_TOKENS = 8000        # per reply
MAX_NUDGES = 3                  # times we re-prompt a model that stops early or gets cut off
REPORTS = Path(__file__).parent / "reports"

# Detection thresholds (change vs. the facility's / state's previous loaded quarter)
FACILITY_HPRD_DROP = -0.75      # hours per resident day
FACILITY_CONTRACT_RISE = 0.15   # share points (0.15 = 15 percentage points)
STATE_HPRD_CHANGE = 0.08
STATE_CONTRACT_CHANGE = 0.015
STATE_WATCHLIST_CHANGE = 5
MAX_CANDIDATES = 15             # facilities handed to the agent (largest moves first)


# ---------------------------------------------------------------- 1. detect (no LLM)

def latest_quarter() -> str:
    return run_sql("select max(quarter) as q from marts.mart_facility_quarter")["rows"][0][0]


def detect(quarter: str) -> dict:
    q = _quarter_literal(quarter)
    facilities = run_sql(f"""
        select ccn, provider_name, state, city, certified_beds, prev_quarter,
               round(hprd, 2) as hprd, round(hprd_change, 2) as hprd_change,
               round(contract_share * 100, 1) as contract_pct,
               round(contract_share_change * 100, 1) as contract_pct_change,
               days_reported, days_below_low_threshold
        from marts.mart_facility_quarter
        where quarter = '{q}' and not is_reporting_gap and prev_quarter is not null
          and (hprd_change <= {FACILITY_HPRD_DROP} or contract_share_change >= {FACILITY_CONTRACT_RISE})
        order by greatest(abs(hprd_change), abs(contract_share_change) * 5) desc
        limit {MAX_CANDIDATES}
    """)
    counts = run_sql(f"""
        select count_if(hprd_change <= {FACILITY_HPRD_DROP}) as big_hprd_drops,
               count_if(contract_share_change >= {FACILITY_CONTRACT_RISE}) as big_contract_rises,
               count(*) as facilities
        from marts.mart_facility_quarter
        where quarter = '{q}' and not is_reporting_gap and prev_quarter is not null
    """)
    new_gaps = run_sql(f"""
        select cur.ccn, cur.provider_name, cur.state, round(prev.hprd, 2) as prev_hprd, round(cur.hprd, 2) as hprd
        from marts.mart_facility_quarter cur
        join marts.mart_facility_quarter prev on prev.ccn = cur.ccn and prev.quarter = cur.prev_quarter
        where cur.quarter = '{q}' and cur.is_reporting_gap and not prev.is_reporting_gap
        order by cur.state limit 20
    """)
    states = run_sql(f"""
        with s as (
            select state, quarter, hprd, contract_share, watchlist_facilities,
                   lag(quarter) over (partition by state order by quarter) as prev_quarter,
                   hprd - lag(hprd) over (partition by state order by quarter) as hprd_change,
                   contract_share - lag(contract_share) over (partition by state order by quarter) as contract_change,
                   watchlist_facilities - lag(watchlist_facilities) over (partition by state order by quarter) as watchlist_change
            from marts.mart_state_quarter
        )
        select state, prev_quarter, round(hprd, 2) as hprd, round(hprd_change, 2) as hprd_change,
               round(contract_share * 100, 1) as contract_pct, round(contract_change * 100, 1) as contract_pct_change,
               watchlist_facilities, watchlist_change
        from s
        where quarter = '{q}' and prev_quarter is not null
          and (abs(hprd_change) >= {STATE_HPRD_CHANGE} or abs(contract_change) >= {STATE_CONTRACT_CHANGE}
               or abs(watchlist_change) >= {STATE_WATCHLIST_CHANGE})
        order by abs(hprd_change) desc
    """)
    return {
        "quarter": quarter,
        "facility_candidates": _records(facilities),
        "facility_counts": _records(counts)[0],
        "new_reporting_gaps": _records(new_gaps),
        "state_candidates": _records(states),
        "detection_sql": [facilities["sql"], counts["sql"], new_gaps["sql"], states["sql"]],
    }


def _records(result: dict) -> list[dict]:
    return [dict(zip(result["columns"], row)) for row in result["rows"]]


def _quarter_literal(q: str) -> str:
    if not re.fullmatch(r"\d{4}Q[1-4]", q or ""):
        raise ValueError(f"Bad quarter: {q!r} (expected like 2026Q2)")
    return q


# ---------------------------------------------------------------- 2. investigate (agent)

TOOLS = [
    {
        "name": "run_sql",
        "description": "Run ONE read-only Snowflake SELECT against CLIPBOARD_HEALTH.MARTS. Returns a query_id "
                       "(like Q3) that you must cite as evidence, plus columns and up to 200 rows.",
        "input_schema": {"type": "object", "properties": {"sql": {"type": "string"}}, "required": ["sql"]},
    },
    {
        "name": "get_facility_profile",
        "description": "Every loaded quarter for one facility (HPRD, contract share, days reported, low-staffing "
                       "days, reporting-gap flag) plus its attributes (beds, ownership, chain, star ratings, "
                       "turnover). Returns a query_id to cite.",
        "input_schema": {"type": "object", "properties": {"ccn": {"type": "string", "description": "6-character CMS provider number"}}, "required": ["ccn"]},
    },
    {
        "name": "compare_quarters",
        "description": "Every loaded quarter for one state: HPRD, share of facilities below 3.0, contract share, "
                       "watchlist count, facility count. Returns a query_id to cite.",
        "input_schema": {"type": "object", "properties": {"state": {"type": "string", "description": "2-letter code, e.g. TX"}}, "required": ["state"]},
    },
    {
        "name": "search_docs",
        "description": "Search CMS PBJ documentation and the project metric glossary (definitions, exclusions, "
                       "reporting rules). Returns passages with ids like C12.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    },
    {
        "name": "record_finding",
        "description": "Record one finding for the staffing brief. Must cite at least one query_id from this run "
                       "that shows the numbers you state. Rejected otherwise.",
        "input_schema": {
            "type": "object",
            "properties": {
                "entity": {"type": "string", "description": "Facility name + CCN, or state code, or 'National'"},
                "entity_type": {"type": "string", "enum": ["facility", "state", "national", "data_quality"]},
                "severity": {"type": "string", "enum": ["high", "medium", "low"]},
                "headline": {"type": "string", "description": "One sentence with the key numbers"},
                "assessment": {"type": "string", "description": "2-4 sentences: what the evidence shows, and whether it looks like a real staffing change or a reporting artifact, and why"},
                "recommended_action": {"type": "string"},
                "evidence": {"type": "array", "items": {"type": "string"}, "description": "query_ids, e.g. ['Q4','Q7']"},
                "doc_citations": {"type": "array", "items": {"type": "string"}, "description": "search_docs passage ids used, if any"},
            },
            "required": ["entity", "entity_type", "severity", "headline", "assessment", "recommended_action", "evidence"],
        },
    },
    {
        "name": "finish",
        "description": "End the run with an executive summary (3-5 sentences) of the quarter.",
        "input_schema": {"type": "object", "properties": {"summary": {"type": "string"}}, "required": ["summary"]},
    },
]

SYSTEM = """You are a staffing monitor for operations leaders at a healthcare staffing company. A new quarter of
CMS Payroll-Based Journal nurse staffing data was just loaded. Detection SQL has already flagged candidate
changes. Your job: investigate them, separate real staffing changes from reporting artifacts, and record
evidence-backed findings for a staffing brief.

How to work:
- Investigate the largest facility moves (aim for 6-10 facilities) and every flagged state. Use
  get_facility_profile and compare_quarters first, run_sql for anything else, search_docs for rules.
- A real staffing change usually shows full days reported, a stable census, and a move that persists or
  fits the facility's history. A reporting artifact usually shows few days reported, a census swing, a
  one-quarter spike or crash, or a special unit (e.g. transitional care). Say which, and why.
- Severity:
  high   = likely real and material for residents or for staffing demand: e.g. a facility falling well below
           3.0 HPRD with full reporting, a facility with 10+ low-staffing days, or a state-wide move.
  medium = notable and plausible but uncertain, or moderate size.
  low    = likely a reporting artifact or data-quality issue worth logging.
- Every number in a finding must appear in a query result from this run, and the finding must cite those
  query_ids in `evidence`. Never state numbers from memory.
- Context: the loaded quarters are 2024Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2, so 2025Q3's "previous quarter"
  is five quarters back. Reporting-gap facilities (IS_REPORTING_GAP) are excluded from national and state
  figures. HPRD is weighted (hours / resident-days). 3.0 HPRD is an analysis reference, not a regulation.
- You are read-only and cannot change data. Recommend actions; don't claim to have taken them.
- Record each finding with record_finding as soon as you have confirmed it; don't save them all for the end.
  At most 2 record_finding calls per reply, assessments of 2-4 sentences.
- When done, call finish with an executive summary. You have a limited number of tool calls; prioritize.
  Aim for 5-10 findings, including reporting artifacts worth logging at low severity.

Database CLIPBOARD_HEALTH, schema MARTS:
{schema}
"""


class Run:
    """State for one monitor run: tool execution, evidence registry, budget, and trace log."""

    def __init__(self, quarter: str, trace_path: Path):
        self.quarter = quarter
        self.trace_path = trace_path
        self.queries: dict[str, dict] = {}      # query_id -> {"sql", "rows"/"error"}
        self.passages: dict[str, dict] = {}
        self.findings: list[dict] = []
        self.summary = ""
        self.tool_calls = 0
        self.tokens = {"input": 0, "output": 0}
        self.stop_reason = ""

    def trace(self, event: str, **data) -> None:
        with self.trace_path.open("a") as f:
            f.write(json.dumps({"t": datetime.now(timezone.utc).isoformat(), "event": event, **data}, default=str) + "\n")

    def _sql(self, sql: str) -> tuple[str, bool]:
        qid = f"Q{len(self.queries) + 1}"
        try:
            result = run_sql(sql)
            self.queries[qid] = {"sql": result["sql"], "row_count": result["row_count"]}
            return json.dumps({"query_id": qid, **result}, default=str), False
        except Exception as e:
            self.queries[qid] = {"sql": sql, "error": str(e)}
            return json.dumps({"query_id": qid, "error": str(e)}), True

    def execute(self, name: str, args: dict) -> tuple[str, bool]:
        if name == "run_sql":
            return self._sql(args.get("sql", ""))
        if name == "get_facility_profile":
            ccn = str(args.get("ccn", "")).strip().upper()
            if not re.fullmatch(r"[0-9A-Z]{6}", ccn):
                return f"Error: CCN must be 6 letters/digits, got {ccn!r}", True
            return self._sql(f"""
                select f.quarter, round(f.hprd, 2) as hprd, round(f.hprd_change, 2) as hprd_change,
                       round(f.contract_share * 100, 1) as contract_pct, f.days_reported,
                       round(f.avg_census, 1) as avg_census, f.days_below_low_threshold, f.is_reporting_gap,
                       d.provider_name, d.city, d.state, d.provider_type, d.ownership_type, d.chain_name,
                       d.certified_beds, d.overall_rating, d.staffing_rating, d.nursing_staff_turnover_pct,
                       d.special_focus_status
                from marts.mart_facility_quarter f
                left join marts.dim_facility d on d.ccn = f.ccn
                where f.ccn = '{ccn}' order by f.quarter""")
        if name == "compare_quarters":
            state = str(args.get("state", "")).strip().upper()
            if not re.fullmatch(r"[A-Z]{2}", state):
                return f"Error: state must be a 2-letter code, got {state!r}", True
            return self._sql(f"""
                select quarter, facilities, round(hprd, 2) as hprd,
                       round(pct_facilities_below_reference * 100, 1) as pct_below_3,
                       round(contract_share * 100, 1) as contract_pct, watchlist_facilities
                from marts.mart_state_quarter where state = '{state}' order by quarter""")
        if name == "search_docs":
            passages = search_docs(args.get("query", ""), k=4)
            for p in passages:
                self.passages.setdefault(p["id"], p)
            return json.dumps(passages), False
        if name == "record_finding":
            evidence = [e for e in args.get("evidence", []) if e in self.queries and "error" not in self.queries[e]]
            if not evidence:
                return ("Rejected: cite at least one successful query_id from this run in `evidence` "
                        f"(you cited {args.get('evidence')}). Run the query first if needed."), True
            finding = {**args, "evidence": evidence,
                       "doc_citations": [c for c in args.get("doc_citations", []) or [] if c in self.passages]}
            self.findings.append(finding)
            return f"Recorded finding #{len(self.findings)} ({finding['severity']}).", False
        if name == "finish":
            self.summary = args.get("summary", "")
            return "Run finished.", False
        return f"Error: unknown tool {name}", True


def _remind(messages: list, text: str) -> None:
    """Add a note to the last user message (keeps user/assistant turns alternating)."""
    last = messages[-1]
    if isinstance(last["content"], str):
        last["content"] = last["content"] + "\n\n" + text
    else:
        last["content"] = list(last["content"]) + [{"type": "text", "text": text}]


def investigate(detected: dict, trace_path: Path) -> Run:
    run = Run(detected["quarter"], trace_path)
    run.trace("detected", **{k: v for k, v in detected.items() if k != "detection_sql"})
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"].strip())
    system = SYSTEM.format(schema=get_schema_text())
    brief = {k: v for k, v in detected.items() if k != "detection_sql"}
    messages = [{"role": "user", "content":
                 f"Quarter just loaded: {detected['quarter']}.\nDetection results (JSON):\n"
                 f"{json.dumps(brief, default=str, indent=1)}\n\nInvestigate and record findings."}]

    nudges = 0
    while True:
        if run.tokens["input"] + run.tokens["output"] >= TOKEN_BUDGET:
            run.stop_reason = f"token budget reached ({TOKEN_BUDGET:,})"
            break
        resp = client.messages.create(model=MONITOR_MODEL, max_tokens=MAX_OUTPUT_TOKENS, system=system,
                                      tools=TOOLS, messages=messages)
        run.tokens["input"] += resp.usage.input_tokens
        run.tokens["output"] += resp.usage.output_tokens
        run.trace("response", stop_reason=resp.stop_reason, output_tokens=resp.usage.output_tokens)

        if resp.stop_reason == "max_tokens":
            # The reply was cut off (usually too many findings at once). Drop it and ask for smaller steps.
            nudges += 1
            if nudges > MAX_NUDGES:
                run.stop_reason = "replies kept hitting the output limit"
                break
            _remind(messages, "Your last reply was cut off because it was too long. Record at most 2 findings "
                              "per reply, with short assessments.")
            continue

        messages.append({"role": "assistant", "content": resp.content})
        for b in resp.content:
            if b.type == "text" and b.text.strip():
                run.trace("thought", text=b.text)
        if resp.stop_reason != "tool_use":
            # The model ended its turn without calling finish: nudge it to record findings and finish.
            nudges += 1
            if nudges > MAX_NUDGES:
                run.stop_reason = "model stopped without calling finish"
                break
            messages.append({"role": "user", "content":
                             f"You have recorded {len(run.findings)} findings and haven't called finish. Record your "
                             "findings now with record_finding (at most 2 per reply), then call finish."})
            continue

        results, finished = [], False
        for b in resp.content:
            if b.type != "tool_use":
                continue
            run.tool_calls += 1
            if run.tool_calls > MAX_TOOL_CALLS and b.name not in ("record_finding", "finish"):
                content, is_error = "Tool limit reached. Record your remaining findings, then call finish.", True
            else:
                content, is_error = run.execute(b.name, b.input)
            run.trace("tool", name=b.name, input=b.input, is_error=is_error, output=content[:20000])
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": content, "is_error": is_error})
            finished = finished or (b.name == "finish" and not is_error)
        messages.append({"role": "user", "content": results})
        if finished:
            run.stop_reason = "finished"
            break
        if run.tool_calls > MAX_TOOL_CALLS + 10:  # hard stop if it ignores the limit message
            run.stop_reason = f"tool limit reached ({MAX_TOOL_CALLS})"
            break

    run.trace("end", stop_reason=run.stop_reason, tool_calls=run.tool_calls, tokens=run.tokens,
              findings=len(run.findings))
    return run


# ---------------------------------------------------------------- 3. report and act

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def write_brief(detected: dict, run: Run, issues: list[dict], path: Path) -> None:
    fc = detected["facility_counts"]
    findings = sorted(run.findings, key=lambda f: SEVERITY_ORDER.get(f["severity"], 3))
    by_sev = {s: sum(f["severity"] == s for f in findings) for s in SEVERITY_ORDER}
    lines = [
        f"# Staffing brief: {run.quarter}",
        "",
        f"_Generated {datetime.now():%Y-%m-%d %H:%M} by the staffing monitor agent (`{MONITOR_MODEL}`). "
        f"Read-only; every number below comes from a query listed in the evidence appendix._",
        "",
        "## Summary",
        run.summary or "_The agent did not write a summary (see run details)._",
        "",
        f"**Signals detected:** {fc.get('BIG_HPRD_DROPS', 0)} facilities with HPRD down {abs(FACILITY_HPRD_DROP)}+, "
        f"{fc.get('BIG_CONTRACT_RISES', 0)} with contract share up {FACILITY_CONTRACT_RISE * 100:.0f}+ points "
        f"(of {fc.get('FACILITIES', 0):,} facilities with a previous quarter), "
        f"{len(detected['new_reporting_gaps'])} new reporting gaps, {len(detected['state_candidates'])} states past thresholds.",
        f"**Findings:** {by_sev['high']} high, {by_sev['medium']} medium, {by_sev['low']} low.",
        "",
        "## Findings",
    ]
    if not findings:
        lines.append("_No findings recorded._")
    for i, f in enumerate(findings, 1):
        cites = " ".join(f"[{c}]" for c in f.get("doc_citations", []))
        lines += [
            f"### {i}. [{f['severity'].upper()}] {f['entity']}",
            f"**{f['headline']}**",
            "",
            f"{f['assessment']} {cites}".strip(),
            "",
            f"*Recommended action:* {f['recommended_action']}",
            "",
            f"*Evidence:* {', '.join(f['evidence'])}",
            "",
        ]
    if issues:
        lines += ["## GitHub issues", ""]
        lines += [f"- {i['status']}: {i['title']}" + (f" ({i['url']})" if i.get("url") else "") for i in issues]
        lines.append("")
    if run.passages and any(f.get("doc_citations") for f in findings):
        lines += ["## Document sources", ""]
        used = {c for f in findings for c in f.get("doc_citations", [])}
        lines += [f"- [{p['id']}] {p['source']}, {p['location']}" for pid, p in run.passages.items() if pid in used]
        lines.append("")
    lines += [
        "## Run details",
        f"- Stop reason: {run.stop_reason}; tool calls: {run.tool_calls} (limit {MAX_TOOL_CALLS}); "
        f"tokens: {run.tokens['input']:,} in / {run.tokens['output']:,} out (budget {TOKEN_BUDGET:,})",
        "",
        "## Evidence appendix",
        "",
    ]
    cited = {e for f in findings for e in f["evidence"]}
    for qid, q in run.queries.items():
        if qid in cited:
            lines += [f"**{qid}** ({q.get('row_count', 0)} rows)", "```sql", q["sql"].strip(), "```", ""]
    path.write_text("\n".join(lines))


def open_issues(run: Run, brief_path: Path, really: bool) -> list[dict]:
    """One GitHub issue per high-severity finding. Skips titles that are already open."""
    high = [f for f in run.findings if f["severity"] == "high"]
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    planned = [{"title": f"[Staffing monitor] {run.quarter}: {f['entity']}"[:200], "finding": f} for f in high]
    if not really or not token or not repo:
        reason = "dry run" if not really else "no GITHUB_TOKEN/GITHUB_REPOSITORY"
        return [{"title": p["title"], "status": f"would open ({reason})"} for p in planned]

    import urllib.request

    def gh(method: str, url: str, body: dict | None = None):
        req = urllib.request.Request(
            f"https://api.github.com{url}", method=method,
            data=json.dumps(body).encode() if body else None,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json",
                     "X-GitHub-Api-Version": "2022-11-28"},
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())

    existing = {i["title"] for i in gh("GET", f"/repos/{repo}/issues?state=open&labels=staffing-monitor&per_page=100")}
    out = []
    for p in planned:
        if p["title"] in existing:
            out.append({"title": p["title"], "status": "already open"})
            continue
        f = p["finding"]
        body = (f"**{f['headline']}**\n\n{f['assessment']}\n\n**Recommended action:** {f['recommended_action']}\n\n"
                f"Evidence queries: {', '.join(f['evidence'])} (see `{brief_path.name}` in the run artifacts).\n\n"
                f"_Opened automatically by the staffing monitor agent._")
        issue = gh("POST", f"/repos/{repo}/issues",
                   {"title": p["title"], "body": body, "labels": ["staffing-monitor", f"severity:{f['severity']}"]})
        out.append({"title": p["title"], "status": "opened", "url": issue.get("html_url")})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--quarter", help="quarter to review, e.g. 2026Q2 (default: latest loaded)")
    ap.add_argument("--open-issues", action="store_true", help="open GitHub issues for high-severity findings")
    args = ap.parse_args()

    quarter = _quarter_literal(args.quarter or latest_quarter())
    REPORTS.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    trace_path = REPORTS / f"trace_{quarter}_{stamp}.jsonl"
    brief_path = REPORTS / f"staffing_brief_{quarter}.md"

    start = time.time()
    print(f"Detecting changes for {quarter}...")
    detected = detect(quarter)
    print(f"  {len(detected['facility_candidates'])} facility candidates, "
          f"{len(detected['state_candidates'])} states, {len(detected['new_reporting_gaps'])} new reporting gaps")
    print("Investigating (this takes a few minutes)...")
    run = investigate(detected, trace_path)
    issues = open_issues(run, brief_path, args.open_issues)
    write_brief(detected, run, issues, brief_path)

    sev = [f["severity"] for f in run.findings]
    print(f"\nDone in {time.time() - start:.0f}s: {len(run.findings)} findings "
          f"({sev.count('high')} high, {sev.count('medium')} medium, {sev.count('low')} low); "
          f"{run.tool_calls} tool calls; stop reason: {run.stop_reason}")
    for i in issues:
        print(f"  issue {i['status']}: {i['title']}")
    print(f"Brief: {brief_path}\nTrace: {trace_path}")


if __name__ == "__main__":
    main()
