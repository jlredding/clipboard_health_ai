"""Check that the app's read-only Snowflake user works and really is read-only.

Run from ~/projects/clipboard_health_ai with:  python3 test_snowflake.py
Needs: pip install snowflake-connector-python python-dotenv cryptography
"""
import os

from cryptography.hazmat.primitives import serialization
from dotenv import load_dotenv
import snowflake.connector

load_dotenv()

with open(os.path.expanduser(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]), "rb") as f:
    private_key = serialization.load_pem_private_key(f.read(), password=None)

conn = snowflake.connector.connect(
    account=os.environ["SNOWFLAKE_ACCOUNT"],
    user=os.environ["SNOWFLAKE_USER"],
    private_key=private_key,
    role=os.environ["SNOWFLAKE_ROLE"],
    warehouse=os.environ["SNOWFLAKE_WAREHOUSE"],
    database=os.environ["SNOWFLAKE_DATABASE"],
    schema=os.environ["SNOWFLAKE_SCHEMA"],
)
cur = conn.cursor()

# 1. Can it read? Should list the mart tables (fct_facility_day, dim_facility, ...)
cur.execute("show tables in schema marts")
print("Tables the app can see:", [row[1] for row in cur.fetchall()])

# 2. Can it write? This SHOULD fail.
try:
    cur.execute("create table marts.should_not_exist (x int)")
    print("PROBLEM: the app user was able to create a table. It is not read-only.")
    cur.execute("drop table marts.should_not_exist")
except snowflake.connector.errors.ProgrammingError:
    print("Good: write was blocked. The app user is read-only.")

conn.close()
