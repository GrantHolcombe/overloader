"""Migration 0004: the API's database role can use rows and nothing more."""

from sqlalchemy import text

from app.db import get_engine

ROLE = "overloader_app"


def query(sql, **params):
    with get_engine().connect() as conn:
        return conn.execute(text(sql), params).scalar()


def test_role_is_a_plain_login():
    attrs = query(
        "SELECT row(rolsuper, rolcreatedb, rolcreaterole, rolcanlogin)::text "
        "FROM pg_roles WHERE rolname = :r",
        r=ROLE,
    )
    assert attrs == "(f,f,f,t)"


def test_rows_in_app_tables_only():
    for table in ("app_user", "email_login_code", "exercise", "log_entry", "log_set"):
        for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            assert query("SELECT has_table_privilege(:r, :t, :p)", r=ROLE, t=table, p=priv), (
                table,
                priv,
            )
        assert not query("SELECT has_table_privilege(:r, :t, 'TRUNCATE')", r=ROLE, t=table)
    assert not query("SELECT has_table_privilege(:r, 'alembic_version', 'SELECT')", r=ROLE)
    assert not query("SELECT has_schema_privilege(:r, 'public', 'CREATE')", r=ROLE)
    assert query("SELECT has_sequence_privilege(:r, 'log_entry_id_seq', 'USAGE')", r=ROLE)
