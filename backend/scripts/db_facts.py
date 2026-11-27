"""Print facts about a database without showing its connection string.

    .venv\\Scripts\\python scripts\\db_facts.py

Asks for the connection string in a hidden prompt (nothing is echoed or saved) and prints only:
the Neon endpoint ID, the migration version, row counts, and whether dev/test accounts are there.
Safe to share the output; it contains no credentials or personal data beyond the test address.
"""

import getpass
from urllib.parse import urlparse

import psycopg

url = getpass.getpass("Connection string (hidden): ").strip()
host = urlparse(url).hostname or ""
print(
    "endpoint:",
    host.split(".")[0].replace("-pooler", ""),
    "(pooled)" if "-pooler" in host else "(direct)",
)
with psycopg.connect(url) as conn:
    q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731
    tables = [
        r[0]
        for r in conn.execute(
            "select tablename from pg_tables where schemaname='public' order by 1"
        )
    ]
    print("tables:", tables)
    if "alembic_version" in tables:
        print("migration version:", q("select version_num from alembic_version"))
    for t in ("app_user", "log_entry", "log_set", "exercise", "email_login_code"):
        if t in tables:
            print(f"{t} rows:", q(f"select count(*) from {t}"))
    if "app_user" in tables:
        print(
            "dev test account present:",
            q("select exists(select 1 from app_user where email = 'lifter@example.com')"),
        )
        print(
            "example.com accounts:",
            q("select count(*) from app_user where email like '%@example.com'"),
        )
    print(
        "overloader_app role exists:",
        q("select exists(select 1 from pg_roles where rolname = 'overloader_app')"),
    )
