"""Give the API's database role (overloader_app) a new password and hand its connection string
and a fresh JWT secret to the clipboard, without either ever being shown on screen.

    .venv\\Scripts\\python scripts\\set_app_password.py

Why not psql's \\password: it sends the password already encrypted, and Neon only accepts plain
text (it checks the password's strength). Typing ALTER ROLE ... PASSWORD '...' at the psql prompt
works but saves the password in psql's history file.

Steps:
  1. Paste the branch's DIRECT owner connection string (hidden prompt; e.g. prod, database
     overloader, role neondb_owner, pooling off).
  2. A random password is set on overloader_app.
  3. The API's POOLED connection string is built and tested (it can read rows, it can't create
     tables), then copied to the clipboard: paste it into the stack's DatabaseUrl.
  4. Press Enter: a new random JWT secret is copied: paste it into JwtSecret.
  5. Press Enter: the clipboard is cleared.

Nothing is printed or saved. If the strings are lost, run it again (it sets a new password) and
update the stack with the new values. Windows only (uses clip).
"""

import getpass
import secrets
import subprocess
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg import sql

ROLE = "overloader_app"


def to_clipboard(text: str) -> None:
    subprocess.run(["clip"], input=text.encode("ascii"), check=True)


owner_url = getpass.getpass("Direct owner connection string (hidden): ").strip()
parts = urlsplit(owner_url)
host = parts.hostname or ""
if "-pooler" in host:
    raise SystemExit("That's the pooled string; paste the DIRECT one (connection pooling off).")
endpoint = host.split(".")[0]
print(f"endpoint {endpoint}, database {parts.path.lstrip('/')}")

password = secrets.token_urlsafe(32)
with psycopg.connect(owner_url, autocommit=True) as conn:
    exists = conn.execute("select 1 from pg_roles where rolname = %s", (ROLE,)).fetchone()
    if not exists:
        raise SystemExit(f"No {ROLE} role here yet; run the migrations first (deploy-api).")
    conn.execute(
        sql.SQL("ALTER ROLE {} WITH PASSWORD {}").format(
            sql.Identifier(ROLE), sql.Literal(password)
        )
    )
print(f"password set on {ROLE}")

pooled_host = host.replace(endpoint, f"{endpoint}-pooler", 1)
netloc = f"{ROLE}:{quote(password, safe='')}@{pooled_host}"
if parts.port:
    netloc += f":{parts.port}"
app_url = urlunsplit((parts.scheme, netloc, parts.path, parts.query, ""))

with psycopg.connect(app_url) as conn:
    who = conn.execute("select current_user").fetchone()[0]
    exercises = conn.execute("select count(*) from exercise").fetchone()[0]
    try:
        conn.execute("create table _privilege_check (id int)")
        raise SystemExit("PROBLEM: the app role could create a table; don't use it, tell Claude.")
    except psycopg.errors.InsufficientPrivilege:
        conn.rollback()
print(f"pooled login works as {who}: reads rows ({exercises} exercises), can't create tables")

to_clipboard(app_url)
input("\nCopied the API's connection string. Paste it into DatabaseUrl, then press Enter... ")
to_clipboard(secrets.token_urlsafe(48))
input("Copied a new JWT secret. Paste it into JwtSecret, then press Enter... ")
to_clipboard(" ")
print("Clipboard cleared. Done.")
