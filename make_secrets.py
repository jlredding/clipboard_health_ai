"""Build the Streamlit Cloud Secrets text from .env and your Snowflake key, and copy it to the clipboard.

  python3 make_secrets.py                      # copies to clipboard (macOS)
  python3 make_secrets.py --password mycode    # also adds APP_PASSWORD (access code for the app)

Then paste (Cmd+V) into Streamlit Cloud: Manage app -> Settings -> Secrets, replacing what's there.
It also saves .streamlit/secrets.toml (git-ignored) so `streamlit run app.py` works the same locally.
Nothing secret is printed to the screen.
"""
import argparse
import json
import os
import subprocess
import tomllib
from pathlib import Path

from dotenv import dotenv_values

KEYS = ["ANTHROPIC_API_KEY", "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_ROLE",
        "SNOWFLAKE_WAREHOUSE", "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA"]

ap = argparse.ArgumentParser()
ap.add_argument("--password", help="optional access code for the app (APP_PASSWORD)")
args = ap.parse_args()

env = dotenv_values(".env")
missing = [k for k in KEYS + ["SNOWFLAKE_PRIVATE_KEY_PATH"] if not env.get(k)]
if missing:
    raise SystemExit(f"Missing in .env: {', '.join(missing)}")

pem = Path(os.path.expanduser(env["SNOWFLAKE_PRIVATE_KEY_PATH"])).read_text().strip()
if not pem.startswith("-----BEGIN") or "PRIVATE KEY-----" not in pem:
    raise SystemExit("The key file doesn't look like a private key (.p8). Check SNOWFLAKE_PRIVATE_KEY_PATH.")

lines = [f"{k} = {json.dumps(env[k].strip())}" for k in KEYS]
lines.append(f'SNOWFLAKE_PRIVATE_KEY = """\n{pem}\n"""')
if args.password:
    lines.append(f"APP_PASSWORD = {json.dumps(args.password)}")
toml_text = "\n".join(lines) + "\n"

parsed = tomllib.loads(toml_text)  # fails loudly if anything isn't valid TOML
assert parsed["SNOWFLAKE_PRIVATE_KEY"].strip() == pem

Path(".streamlit").mkdir(exist_ok=True)
Path(".streamlit/secrets.toml").write_text(toml_text)
try:
    subprocess.run(["pbcopy"], input=toml_text.encode(), check=True)
    copied = "Copied to your clipboard."
except (FileNotFoundError, subprocess.CalledProcessError):
    copied = "Couldn't reach the clipboard; open .streamlit/secrets.toml and copy it from there."

print(f"Built valid Secrets with {len(parsed)} settings: {', '.join(parsed)}")
print(copied)
print("Paste it into Streamlit Cloud -> Manage app -> Settings -> Secrets (replace everything), then Save.")
