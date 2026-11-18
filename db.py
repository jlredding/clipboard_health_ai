"""Snowflake access for the Clipboard Health AI assistant.

Every query the LLM writes goes through run_sql(), which has four layers of protection:
  1. Snowflake itself: the app logs in as APP_READER_SVC with the CLIPBOARD_READER role,
     which can only SELECT from the MARTS schema (verified by test_snowflake.py).
  2. A statement check here: one statement only, must start with SELECT/WITH,
     no write or admin keywords.
  3. A 30-second statement timeout (set on the user and again on this session).
  4. A row cap: at most MAX_ROWS rows are fetched and sent back to the model.
"""
import atexit
import datetime as dt
import decimal
import os
import re
from functools import lru_cache

import snowflake.connector
from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv

load_dotenv()

MAX_ROWS = 200
TIMEOUT_SECONDS = 30

FORBIDDEN = re.compile(
    r"\b(insert|update|delete|merge|create|alter|drop|truncate|undrop|grant|revoke|"
    r"copy|put|remove|call|execute|begin|commit|rollback)\b",
    re.IGNORECASE,
)


class UnsafeQueryError(ValueError):
    """Raised when a query fails the read-only check (before it reaches Snowflake)."""


def check_sql(sql: str) -> str:
    """Return the cleaned query if it is a single read-only SELECT, else raise UnsafeQueryError."""
    s = re.sub(r"/\*.*?\*/", " ", sql or "", flags=re.DOTALL)  # block comments
    s = re.sub(r"--[^\n]*", " ", s)                             # line comments
    s = s.strip().rstrip(";").strip()
    if not s:
        raise UnsafeQueryError("Empty query.")

    # Blank out string literals so words inside quotes ('Update pending') don't trip the check.
    no_strings = re.sub(r"'(?:[^']|'')*'", "''", s)
    if ";" in no_strings:
        raise UnsafeQueryError("Only one statement is allowed per query.")
    if not re.match(r"^\s*(select|with)\b", no_strings, re.IGNORECASE):
        raise UnsafeQueryError("Only SELECT queries are allowed.")
    bad = FORBIDDEN.search(no_strings)
    if bad:
        raise UnsafeQueryError(f"Keyword not allowed in a read-only query: {bad.group(0).upper()}")
    return s


def _private_key():
    # Locally: a path to the .p8 file. On Streamlit Cloud: the key text itself in SNOWFLAKE_PRIVATE_KEY.
    pem = os.environ.get("SNOWFLAKE_PRIVATE_KEY")
    if pem:
        data = pem.encode()
    else:
        with open(os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]), "rb") as f:
            data = f.read()
    return serialization.load_pem_private_key(data, password=None)


@lru_cache(maxsize=1)
def get_connection():
    conn = snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        private_key=_private_key(),
        role=os.environ["SNOWFLAKE_ROLE"],
        warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
        database=os.environ["SNOWFLAKE_DATABASE"],
        schema=os.environ["SNOWFLAKE_SCHEMA"],
        session_parameters={
            "STATEMENT_TIMEOUT_IN_SECONDS": TIMEOUT_SECONDS,
            "QUERY_TAG": "clipboard_health_ai",
        },
        enable_server_session_keep_alive_auto_detection=False,
    )
    atexit.register(conn.close)  # close cleanly when the script ends
    return conn


def _jsonable(v):
    if isinstance(v, decimal.Decimal):
        return float(v)
    if isinstance(v, (dt.date, dt.datetime)):
        return v.isoformat()
    return v


def _execute(sql: str):
    cur = get_connection().cursor()
    try:
        cur.execute(sql)
        columns = [d[0] for d in cur.description]
        rows = cur.fetchmany(MAX_ROWS + 1)  # fetch one extra to know if we truncated
    finally:
        cur.close()
    return columns, rows


def run_sql(sql: str) -> dict:
    """Run one read-only query. Returns columns, up to MAX_ROWS rows, and whether rows were cut off."""
    clean = check_sql(sql)
    try:
        columns, rows = _execute(clean)
    except snowflake.connector.errors.Error as e:
        # A long-running app (Streamlit) can outlive its Snowflake session: reconnect once and retry.
        if "expired" not in str(e).lower() and "connection" not in str(e).lower():
            raise
        get_connection.cache_clear()
        columns, rows = _execute(clean)
    truncated = len(rows) > MAX_ROWS
    rows = rows[:MAX_ROWS]
    return {
        "sql": clean,
        "columns": columns,
        "rows": [[_jsonable(v) for v in r] for r in rows],
        "row_count": len(rows),
        "truncated": truncated,
    }


@lru_cache(maxsize=1)
def get_schema_text() -> str:
    """Describe every MARTS table and column, for the model's system prompt."""
    cur = get_connection().cursor()
    try:
        cur.execute(
            "select table_name, column_name, data_type "
            "from information_schema.columns "
            "where table_schema = 'MARTS' "
            "order by table_name, ordinal_position"
        )
        tables: dict[str, list[str]] = {}
        for table, column, dtype in cur.fetchall():
            tables.setdefault(table, []).append(f"{column} {dtype}")
    finally:
        cur.close()
    return "\n".join(f"- MARTS.{t}: {', '.join(cols)}" for t, cols in tables.items())
