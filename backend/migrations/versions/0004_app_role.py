"""A least-privilege login role for the API: overloader_app.

It can read and write rows in the app's tables and use their id sequences, and nothing else: it
can't create, alter or drop tables, create roles, change grants, or touch alembic_version.
Migrations and the catalog sync keep running as the database owner (neondb_owner on Neon).

Tables created by later migrations get the same grants automatically (ALTER DEFAULT PRIVILEGES),
so new tables don't need their own GRANT lines.

The role is created WITHOUT a password, so no secret is ever in this file, git or chat. Set it
once per database, connected as the owner, at the psql prompt (it asks twice, shows nothing):
    \\password overloader_app
See infra/README.md.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-27
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ROLE = "overloader_app"


def upgrade() -> None:
    op.execute(f"""
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{ROLE}') THEN
            CREATE ROLE {ROLE} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
          END IF;
          EXECUTE format('GRANT CONNECT ON DATABASE %I TO {ROLE}', current_database());
        END $$;
    """)
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA public FROM {ROLE}")
    # Rows in every existing table and the sequences behind their ids...
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {ROLE}")
    op.execute(f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO {ROLE}")
    # ...but not the migration bookkeeping.
    op.execute(f"REVOKE ALL ON alembic_version FROM {ROLE}")
    # The same for tables and sequences that later migrations (run as this owner) create.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE current_user IN SCHEMA public "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {ROLE}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE current_user IN SCHEMA public "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {ROLE}"
    )


def downgrade() -> None:
    # Takes the grants away; the role itself is left, since other databases on the same
    # Postgres server (or its password) may still use it. DROP ROLE by hand if it's unwanted.
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE current_user IN SCHEMA public "
        f"REVOKE USAGE, SELECT ON SEQUENCES FROM {ROLE}"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES FOR ROLE current_user IN SCHEMA public "
        f"REVOKE SELECT, INSERT, UPDATE, DELETE ON TABLES FROM {ROLE}"
    )
    op.execute(f"REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM {ROLE}")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA public FROM {ROLE}")
    op.execute(f"""
        DO $$ BEGIN
          EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM {ROLE}', current_database());
        END $$;
    """)
