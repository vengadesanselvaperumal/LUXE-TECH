from __future__ import annotations

import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dotenv import dotenv_values
import psycopg
from psycopg.conninfo import make_conninfo
from psycopg import sql
from sqlalchemy.engine import make_url


ROOT = Path(__file__).resolve().parent
BACKEND = ROOT / "backend"
MIGRATION_TABLES = {
    ("public", "alembic_version"),
    ("public", "schema_migrations"),
    ("supabase_migrations", "schema_migrations"),
}


def _say(message: str) -> None:
    print(message, flush=True)


def _normalized_type(value: str) -> str:
    value = " ".join(value.lower().split())
    return {
        "character varying": "varchar",
        "double precision": "float",
        "real": "float",
        "timestamp with time zone": "timestamp with time zone",
        "timestamp without time zone": "timestamp without time zone",
    }.get(value, value)


def _project_reference_matches(database_url: Any, supabase_url: Any) -> bool:
    if not isinstance(supabase_url, str):
        return False

    api_host = urlparse(supabase_url).hostname
    if not api_host or not api_host.endswith(".supabase.co"):
        return False
    api_reference = api_host[: -len(".supabase.co")]
    if not api_reference or "." in api_reference:
        return False

    database_references = []
    if database_url.username and database_url.username.startswith("postgres."):
        database_references.append(database_url.username.removeprefix("postgres."))

    database_host = database_url.host or ""
    if database_host.startswith("db.") and database_host.endswith(".supabase.co"):
        database_references.append(
            database_host[len("db.") : -len(".supabase.co")]
        )

    return bool(database_references) and all(
        reference == api_reference for reference in database_references
    )


def _connection_failure_category(exc: Exception) -> str:
    message = str(exc).lower()
    if "password authentication failed" in message:
        return "server reachable; PostgreSQL rejected the configured authentication credentials"
    if "tenant or user not found" in message:
        return "pooler reachable; verify the Supabase pooler username and project reference"
    if "could not translate host name" in message or "name or service not known" in message:
        return "hostname could not be resolved; verify the Dashboard connection host"
    if "timed out" in message or "timeout expired" in message:
        return "connection timed out; verify network access, port, and Supabase connection mode"
    if "certificate" in message or "ssl" in message:
        return "TLS negotiation failed; verify the Dashboard connection URI and SSL requirements"
    return "connection failed; verify the Dashboard URI, network access, and database role"


def main() -> int:
    env_path = ROOT / ".env"
    if not env_path.is_file():
        _say("Configuration error: root .env file was not found.")
        return 2

    database_url = dotenv_values(env_path).get("DATABASE_URL")
    supabase_url = dotenv_values(env_path).get("SUPABASE_URL")
    if not database_url:
        _say("Configuration error: DATABASE_URL is missing from the root .env.")
        return 2

    try:
        url = make_url(database_url)
    except (TypeError, ValueError):
        _say("Configuration error: DATABASE_URL is not a valid SQLAlchemy URL.")
        return 2

    if url.drivername not in {"postgresql", "postgresql+psycopg"}:
        _say("Configuration error: DATABASE_URL must use a PostgreSQL SQLAlchemy driver.")
        return 2
    if not all((url.username, url.password, url.host, url.port, url.database)):
        _say("Configuration error: DATABASE_URL is missing a required connection field.")
        return 2
    if url.query.get("sslmode") != "require":
        _say("Configuration error: DATABASE_URL must require SSL (sslmode=require).")
        return 2
    if not _project_reference_matches(url, supabase_url):
        _say(
            "Safety stop: the Supabase API URL and database connection could not "
            "be confirmed as the same project; no database connection was attempted."
        )
        return 2
    _say("Local target check: API and database settings identify the same Supabase project.")

    if str(BACKEND) not in sys.path:
        sys.path.insert(0, str(BACKEND))

    try:
        from app.database import Base, engine as application_engine
    except Exception as exc:
        _say(f"Application configuration error: {type(exc).__name__}; URI details suppressed.")
        return 2

    inspection_stage = "application URL verification"
    try:
        if application_engine.url != url:
            _say(
                "Configuration error: the application's effective database URL does not "
                "match the root .env value; no database connection was attempted."
            )
            return 2

        conninfo = make_conninfo(
            host=url.host,
            port=url.port,
            dbname=url.database,
            user=url.username,
            password=url.password,
            sslmode="require",
            connect_timeout=10,
        )
        _say("Connection attempt: PostgreSQL via psycopg (connection details suppressed).")

        inspection_stage = "opening the database connection"
        with psycopg.connect(conninfo=conninfo, autocommit=True) as connection:
            with connection.cursor() as cursor:
                inspection_stage = "starting an explicitly read-only transaction"
                cursor.execute("BEGIN READ ONLY")
                inspection_stage = "verifying database identity and read-only state"
                cursor.execute(
                    "SELECT current_database(), current_user, current_schema(), "
                    "current_setting('transaction_read_only')"
                )
                identity = cursor.fetchone()
                if identity is None or str(identity[3]).lower() not in {"on", "true", "1"}:
                    _say(
                        "Safety stop: the database did not confirm a read-only transaction; "
                        "no catalog inspection queries were run."
                    )
                    cursor.execute("ROLLBACK")
                    return 3

                _say(
                    "Connection verified; database, role, and schema identifiers "
                    f"suppressed; transaction_read_only={identity[3]}."
                )
                cursor.execute(
                    """
                    SELECT role.rolsuper, role.rolbypassrls,
                           has_table_privilege(current_user, 'storage.buckets', 'SELECT'),
                           has_table_privilege(current_user, 'storage.objects', 'SELECT')
                    FROM pg_catalog.pg_roles AS role
                    WHERE role.rolname = current_user
                    """
                )
                role_capabilities = cursor.fetchone()
                if role_capabilities is not None:
                    _say(
                        "Auditor role capabilities (identity suppressed): "
                        f"superuser={role_capabilities[0]}; "
                        f"bypass_rls={role_capabilities[1]}; "
                        f"storage_buckets_select={role_capabilities[2]}; "
                        f"storage_objects_select={role_capabilities[3]}."
                    )

                inspection_stage = "reading information_schema and PostgreSQL catalogs"
                cursor.execute(
                    """
                    SELECT table_schema, table_name, table_type
                    FROM information_schema.tables
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND (
                          table_schema IN ('public', 'supabase_migrations')
                          OR (table_schema = 'storage' AND table_name IN ('objects', 'buckets'))
                      )
                    ORDER BY table_schema, table_name
                    """
                )
                tables = cursor.fetchall()
                _say("Visible non-system tables:")
                for row in tables:
                    _say(f"  {row[0]}.{row[1]} ({row[2]})")

                cursor.execute(
                    """
                    SELECT table_schema, table_name, column_name, data_type,
                           udt_name, is_nullable, column_default,
                           character_maximum_length, numeric_precision, numeric_scale
                    FROM information_schema.columns
                    WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
                      AND (
                          table_schema IN ('public', 'supabase_migrations')
                          OR (table_schema = 'storage' AND table_name IN ('objects', 'buckets'))
                      )
                    ORDER BY table_schema, table_name, ordinal_position
                    """
                )
                columns = cursor.fetchall()
                columns_by_table: dict[tuple[str, str], list[Any]] = {}
                for row in columns:
                    columns_by_table.setdefault((row[0], row[1]), []).append(row)

                _say("Visible columns and types:")
                for (schema_name, table_name), rows in sorted(columns_by_table.items()):
                    rendered = ", ".join(
                        f"{row[2]}:{row[3]} (udt={row[4]}, nullable={row[5]}, "
                        f"default={row[6]}, length={row[7]}, "
                        f"precision={row[8]}, scale={row[9]})"
                        for row in rows
                    )
                    _say(f"  {schema_name}.{table_name}: {rendered}")

                model_table_names = list(Base.metadata.tables)
                cursor.execute(
                    """
                    SELECT n.nspname, c.relname, c.relkind, c.relrowsecurity,
                           c.relforcerowsecurity
                    FROM pg_catalog.pg_class AS c
                    JOIN pg_catalog.pg_namespace AS n ON n.oid = c.relnamespace
                    WHERE (
                          (n.nspname = 'public' AND c.relname = ANY(%s))
                          OR (n.nspname = 'storage' AND c.relname IN ('objects', 'buckets'))
                      )
                      AND c.relkind IN ('r', 'p', 'v', 'm', 'f')
                    ORDER BY n.nspname, c.relname
                    """,
                    (model_table_names,),
                )
                catalog_relations = cursor.fetchall()
                catalog_by_name = {row[1]: row for row in catalog_relations}
                visible_public = {
                    table_name
                    for schema_name, table_name in columns_by_table
                    if schema_name == "public"
                }

                _say("ORM-to-public-schema comparison:")
                for table_name, model_table in sorted(Base.metadata.tables.items()):
                    catalog_row = catalog_by_name.get(table_name)
                    if catalog_row is None:
                        _say(
                            f"  {table_name}: not found in visible public pg_class "
                            "(absence is unconfirmed; catalog visibility may be restricted)"
                        )
                        continue
                    if table_name not in visible_public:
                        _say(
                            f"  {table_name}: relation exists in pg_class, but columns are "
                            "not visible in information_schema for this role"
                        )
                        continue

                    actual_columns = columns_by_table.get(("public", table_name), [])
                    actual_by_name = {row[2]: row for row in actual_columns}
                    expected_names = set(model_table.columns.keys())
                    actual_names = set(actual_by_name)
                    missing = sorted(expected_names - actual_names)
                    extra = sorted(actual_names - expected_names)
                    mismatched_types = []
                    mismatched_nullability = []
                    for column_name in sorted(expected_names & actual_names):
                        model_column = model_table.columns[column_name]
                        expected_type = model_column.type.compile(dialect=application_engine.dialect)
                        actual_column = actual_by_name[column_name]
                        actual_type = actual_column[3]
                        if _normalized_type(expected_type) != _normalized_type(actual_type):
                            mismatched_types.append(
                                f"{column_name}: model={expected_type}, database={actual_type}"
                            )
                        actual_nullable = actual_column[5] == "YES"
                        if bool(model_column.nullable) != actual_nullable:
                            mismatched_nullability.append(
                                f"{column_name}: model_nullable={model_column.nullable}, "
                                f"database_nullable={actual_nullable}"
                            )
                    status = "match" if not (
                        missing or extra or mismatched_types or mismatched_nullability
                    ) else "differences"
                    _say(
                        f"  {table_name}: {status}; missing={missing}; extra={extra}; "
                        f"type_differences={mismatched_types}; "
                        f"nullability_differences={mismatched_nullability}; "
                        f"rls_enabled={catalog_row[3]}; force_rls={catalog_row[4]}"
                    )
                _say("Storage relation RLS status:")
                for relation in sorted(
                    (row for row in catalog_relations if row[0] == "storage"),
                    key=lambda row: row[1],
                ):
                    _say(
                        f"  storage.{relation[1]}: "
                        f"rls_enabled={relation[3]}; force_rls={relation[4]}"
                    )

                cursor.execute(
                    """
                    SELECT ns.nspname, tbl.relname, con.conname,
                           con.contype, pg_get_constraintdef(con.oid, true)
                    FROM pg_catalog.pg_constraint AS con
                    JOIN pg_catalog.pg_class AS tbl ON tbl.oid = con.conrelid
                    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = tbl.relnamespace
                    WHERE (ns.nspname = 'public' AND tbl.relname = ANY(%s))
                       OR (ns.nspname = 'storage' AND tbl.relname IN ('objects', 'buckets'))
                    ORDER BY tbl.relname, con.contype, con.conname
                    """,
                    (model_table_names,),
                )
                _say("Visible application/storage constraints:")
                for row in cursor.fetchall():
                    _say(f"  {row[0]}.{row[1]} {row[3]} {row[2]}: {row[4]}")

                cursor.execute(
                    """
                    SELECT schemaname, tablename, indexname, indexdef
                    FROM pg_catalog.pg_indexes
                    WHERE (schemaname = 'public' AND tablename = ANY(%s))
                       OR (schemaname = 'storage' AND tablename IN ('objects', 'buckets'))
                    ORDER BY tablename, indexname
                    """,
                    (model_table_names,),
                )
                _say("Visible application/storage indexes:")
                for row in cursor.fetchall():
                    _say(f"  {row[0]}.{row[1]} {row[2]}: {row[3]}")

                cursor.execute(
                    """
                    SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check
                    FROM pg_catalog.pg_policies
                    WHERE schemaname IN ('public', 'storage')
                    ORDER BY schemaname, tablename, policyname
                    """
                )
                policies = cursor.fetchall()
                _say("Visible public/storage RLS policies:")
                if not policies:
                    _say("  none visible to this role")
                for row in policies:
                    _say(
                        f"  {row[0]}.{row[1]} {row[2]} roles={row[3]} "
                        f"command={row[4]} using={row[5]} check={row[6]}"
                    )

                cursor.execute(
                    """
                    SELECT table_schema, table_name, grantee, privilege_type,
                           is_grantable
                    FROM information_schema.table_privileges
                    WHERE (table_schema = 'public' AND table_name = ANY(%s))
                       OR (table_schema = 'storage' AND table_name IN ('objects', 'buckets'))
                    ORDER BY table_schema, table_name, grantee, privilege_type
                    """,
                    (model_table_names,),
                )
                _say("Visible table grants:")
                for row in cursor.fetchall():
                    _say(
                        f"  {row[0]}.{row[1]} grantee={row[2]} "
                        f"privilege={row[3]} grantable={row[4]}"
                    )

                cursor.execute("SAVEPOINT storage_bucket_metadata_read")
                try:
                    cursor.execute(
                        """
                        SELECT id, name, public
                        FROM storage.buckets
                        ORDER BY id
                        """
                    )
                    bucket_rows = cursor.fetchall()
                    cursor.execute("RELEASE SAVEPOINT storage_bucket_metadata_read")
                    _say(
                        "Storage bucket metadata (id/name/public only; "
                        f"visible rows under current role/RLS={len(bucket_rows)}):"
                    )
                    for row in bucket_rows:
                        _say(f"  {row[0]} name={row[1]} public={row[2]}")
                except psycopg.Error as exc:
                    cursor.execute("ROLLBACK TO SAVEPOINT storage_bucket_metadata_read")
                    cursor.execute("RELEASE SAVEPOINT storage_bucket_metadata_read")
                    _say(
                        "Storage bucket metadata unavailable to this role "
                        f"({type(exc).__name__}); SQLSTATE={exc.sqlstate}."
                    )

                cursor.execute(
                    """
                    SELECT extname
                    FROM pg_catalog.pg_extension
                    WHERE extname = 'uuid-ossp'
                    """
                )
                _say(
                    "UUID extension uuid-ossp: "
                    + ("installed" if cursor.fetchone() else "not visible as installed")
                )

                cursor.execute(
                    """
                    SELECT tg.tgname, tbl.relname,
                           pg_get_triggerdef(tg.oid, true)
                    FROM pg_catalog.pg_trigger AS tg
                    JOIN pg_catalog.pg_class AS tbl ON tbl.oid = tg.tgrelid
                    JOIN pg_catalog.pg_namespace AS ns ON ns.oid = tbl.relnamespace
                    WHERE ns.nspname = 'public'
                      AND NOT tg.tgisinternal
                      AND tbl.relname = ANY(%s)
                    ORDER BY tbl.relname, tg.tgname
                    """,
                    (model_table_names,),
                )
                _say("Visible application triggers:")
                trigger_rows = cursor.fetchall()
                if not trigger_rows:
                    _say("  none visible")
                for row in trigger_rows:
                    _say(f"  public.{row[1]} {row[0]}: {row[2]}")

                migration_tables = sorted(set(columns_by_table) & MIGRATION_TABLES)
                _say("Migration metadata:")
                if not migration_tables:
                    _say(
                        "  no known migration metadata table is visible; "
                        "this does not prove no migration history exists"
                    )
                for schema_name, table_name in migration_tables:
                    version_columns = [
                        row[2]
                        for row in columns_by_table[(schema_name, table_name)]
                        if row[2] in {"version", "version_num", "name", "executed_at"}
                    ]
                    if not version_columns:
                        _say(
                            f"  {schema_name}.{table_name} exists; "
                            "no recognized version metadata columns are visible"
                        )
                        continue
                    try:
                        cursor.execute("SAVEPOINT migration_metadata_read")
                        cursor.execute(
                            sql.SQL("SELECT {} FROM {}.{} LIMIT 100").format(
                                sql.SQL(", ").join(map(sql.Identifier, version_columns)),
                                sql.Identifier(schema_name),
                                sql.Identifier(table_name),
                            )
                        )
                        versions = cursor.fetchall()
                        cursor.execute("RELEASE SAVEPOINT migration_metadata_read")
                        _say(
                            f"  {schema_name}.{table_name} metadata columns "
                            f"{version_columns}; visible version records={len(versions)}"
                        )
                        for version in versions:
                            _say(f"    {version}")
                    except psycopg.Error as exc:
                        cursor.execute("ROLLBACK TO SAVEPOINT migration_metadata_read")
                        cursor.execute("RELEASE SAVEPOINT migration_metadata_read")
                        _say(
                            f"  {schema_name}.{table_name} metadata read unavailable "
                            f"({type(exc).__name__}); SQLSTATE={exc.sqlstate}; details suppressed"
                        )

                cursor.execute("ROLLBACK")

        _say("Inspection completed. No migration, DDL, DML, or storage operation was run.")
        return 0
    except (psycopg.Error, OSError) as exc:
        sqlstate = getattr(exc, "sqlstate", None)
        sqlstate_text = f"; SQLSTATE={sqlstate}" if sqlstate else ""
        _say(
            f"Read-only inspection failed while {inspection_stage} "
            f"({type(exc).__name__}{sqlstate_text}); "
            f"reason={_connection_failure_category(exc)}; "
            "connection details suppressed. Verify Supabase URI, network access, "
            "and read privileges; read-only verification is incomplete."
        )
        return 1
    finally:
        application_engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
