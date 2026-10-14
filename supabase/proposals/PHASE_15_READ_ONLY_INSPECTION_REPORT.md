# LUXE.TECH — Phase 15: Read-Only Supabase Pre-Deployment Inspection Report

**Document Location:** `supabase/proposals/PHASE_15_READ_ONLY_INSPECTION_REPORT.md`  
**Status:** LOCAL PREPARATION & FINAL SAFETY GATE (Awaiting User Authorization)  
**Execution Mode:** STRICTLY LOCAL REVIEW — ZERO REMOTE CONNECTIONS INITIATED IN PHASE 15  
**Target:** Dedicated LUXE.TECH Supabase Project  
**Date:** October 10, 2026  

---

## 1. Executive Summary & Verification State

Phase 15 establishes the pre-deployment verification gate for the dedicated LUXE.TECH Supabase project.

> [!IMPORTANT]
> **CRITICAL VERIFICATION DISTINCTION:**
> **No remote connection has been initiated in Phase 15.** Zero queries have been run against the remote database in this phase.
> Any prior observations regarding missing application tables, storage buckets, or installed extensions are **historical observations from the Phase 06 baseline audit**, NOT freshly verified in Phase 15. The remote database state in Phase 15 remains **PENDING CURRENT INSPECTION**.

### Approved Project Decisions Maintained:
1. **Authentication Engine:** Retain FastAPI custom JWT authentication (`public.users` + PBKDF2 hashing). Supabase Auth (`auth.users`) is not used.
2. **Image Ownership:** Defer adding relational `images.user_id` to a future coordinated ORM and database migration (Migration 003). Retain 13-column physical baseline matching `ImageRecord`.
3. **Inspection Scope:** Prepare a strictly read-only catalog inspection of the dedicated LUXE.TECH Supabase project.
4. **Strict Safety Invariants:** Zero migrations applied, zero cloud resources modified, zero DDL/DML executed, zero roles created.

---

## 2. Verification of `inspect_supabase_readonly.py` Safety Architecture

The standalone inspection script [`inspect_supabase_readonly.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/inspect_supabase_readonly.py) was thoroughly reviewed across 6 vital safety dimensions:

| Safety Dimension | Implementation in `inspect_supabase_readonly.py` | Verification Result |
|---|---|:---:|
| **1. Connection Handling & Pool Isolation** | Connects via standalone `psycopg.connect(...)` separate from FastAPI's SQLAlchemy connection pool. Disposes application engine cleanly in `finally` block without executing queries on it. Sets `connect_timeout=10`. | **VERIFIED SAFE** |
| **2. TLS & Transport Security** | Explicitly validates `sslmode=require` in URL and passes `sslmode="require"` in psycopg `conninfo`. Non-SSL connections are hard-rejected before network transmission. | **VERIFIED SAFE** |
| **3. Project Correlation Gate** | `_project_reference_matches(url, supabase_url)` extracts the tenant reference from `DATABASE_URL` (`postgres.<ref>`) and `SUPABASE_URL` (`<ref>.supabase.co`), verifying character-for-character match before opening a socket. | **VERIFIED SAFE** |
| **4. Transaction Read-Only Verification** | Executes `BEGIN READ ONLY;` immediately. Verifies `current_setting('transaction_read_only') == 'on'`. If not confirmed read-only, issues `ROLLBACK;` and terminates with code 3 without executing catalog queries. Engine rejects any DDL/DML (`SQLSTATE 25006`). | **VERIFIED SAFE** |
| **5. Unconditional Rollback & Savepoints** | Executes `cursor.execute("ROLLBACK")` before closing. Uses isolated `SAVEPOINT` blocks for auxiliary metadata reads (`storage.buckets`, migration ledgers) so permission errors roll back cleanly to the savepoint without failing the session. | **VERIFIED SAFE** |
| **6. Secret Redaction & Exception Sanitization** | Connection strings, passwords, project references, database names, and raw role identities are suppressed from stdout. Exception messages are passed through `_connection_failure_category()`, emitting sanitized category descriptions rather than raw database error tracebacks. | **VERIFIED SAFE** |

---

## 3. Database Role Strategy & Elimination of Premature Role DDL

- **Configured Connection Role:** `postgres.[REDACTED-20-CHAR-REF]`.
- **Role Characteristics:** In hosted Supabase, `postgres` is the default database owner role (`NOSUPERUSER`, but possessing table ownership, DDL/DML privileges, and `BYPASSRLS`).
- **No Role Creation Recommended:** No new database roles (e.g. read-only inspector roles) will be created as part of this inspection. Creating unvetted roles in the cloud database is premature and unnecessary.
- **Read-Only Enforcement Level:** Read-only behavior is enforced at the **PostgreSQL transaction level** via `BEGIN READ ONLY;` + `transaction_read_only=on` verification + unconditional `ROLLBACK;`.

---

## 4. Metadata Checks and Minimum Required Privileges

The inspection executes strictly catalog-level queries. Below is the precise breakdown of each inspection check and its minimum privilege requirement:

| Inspection Check | Catalog Query / Function | Target System Catalogs | Minimum Privilege Required |
|---|---|---|---|
| **1. Session & Transaction State** | `SELECT current_database(), current_user, current_schema(), current_setting('transaction_read_only');` | Built-in session functions | `CONNECT` on database (available to any authenticated connection). |
| **2. Role Capabilities** | `SELECT rolsuper, rolbypassrls, has_table_privilege(...) FROM pg_catalog.pg_roles WHERE rolname = current_user;` | `pg_catalog.pg_roles` | Public access to own role record in `pg_roles`. |
| **3. Table Inventory** | `SELECT table_schema, table_name, table_type FROM information_schema.tables WHERE table_schema IN ('public', 'supabase_migrations') ...;` | `information_schema.tables` | Public read on `information_schema` (only shows tables with grants or ownership). |
| **4. Column Inventory & Types** | `SELECT column_name, data_type, udt_name, is_nullable, column_default, ... FROM information_schema.columns WHERE ...;` | `information_schema.columns` | Public read on `information_schema` (only shows columns with grants or ownership). |
| **5. RLS Activation & Status** | `SELECT n.nspname, c.relname, c.relkind, c.relrowsecurity, c.relforcerowsecurity FROM pg_catalog.pg_class c JOIN pg_catalog.pg_namespace n ...;` | `pg_catalog.pg_class`, `pg_catalog.pg_namespace` | Default public read on `pg_catalog`. |
| **6. Constraints (PK, FK, Unique)** | `SELECT conname, contype, pg_get_constraintdef(con.oid, true) FROM pg_catalog.pg_constraint con ...;` | `pg_catalog.pg_constraint`, `pg_catalog.pg_class` | Default public read on `pg_catalog`. |
| **7. Index Definitions** | `SELECT schemaname, tablename, indexname, indexdef FROM pg_catalog.pg_indexes WHERE ...;` | `pg_catalog.pg_indexes` | Default public read on `pg_catalog`. |
| **8. Row Level Security Policies** | `SELECT schemaname, tablename, policyname, roles, cmd, qual, with_check FROM pg_catalog.pg_policies WHERE ...;` | `pg_catalog.pg_policies` | Default public read on `pg_catalog` (PostgreSQL 10+). |
| **9. Table-Level Grants** | `SELECT table_schema, table_name, grantee, privilege_type, is_grantable FROM information_schema.table_privileges WHERE ...;` | `information_schema.table_privileges` | Public read on `information_schema.table_privileges`. |
| **10. Storage Bucket Metadata** | `SELECT id, name, public FROM storage.buckets ORDER BY id;` *(via SAVEPOINT)* | `storage.buckets` | `USAGE ON SCHEMA storage`, `SELECT ON storage.buckets`, and RLS bypass or policy. |
| **11. Extension Verification** | `SELECT extname FROM pg_catalog.pg_extension WHERE extname = 'uuid-ossp';` | `pg_catalog.pg_extension` | Default public read on `pg_catalog.pg_extension`. |
| **12. Trigger Inventory** | `SELECT tg.tgname, tbl.relname, pg_get_triggerdef(tg.oid, true) FROM pg_catalog.pg_trigger tg ...;` | `pg_catalog.pg_trigger`, `pg_catalog.pg_class` | Default public read on `pg_catalog`. |
| **13. Migration Ledger Discovery** | `SELECT <version_columns> FROM <schema>.<migration_table> LIMIT 100;` *(via SAVEPOINT)* | `public.alembic_version`, `public.schema_migrations`, `supabase_migrations.schema_migrations` | `USAGE ON SCHEMA <schema>` and `SELECT ON <table_name>`. |

---

## 5. Discrepancy Baseline Taxonomy & Historical Status

Findings from the inspection will be categorized against [`luxe_phase12_canonical_candidate_migration.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase12_canonical_candidate_migration.sql):

- **VERIFIED:** Remote catalog object matches candidate migration exactly.
- **MISSING:** Expected candidate object is not visible in the remote catalog (and sufficient privileges exist to confirm its absence).
- **CONFLICT:** Remote object exists but differs in type, nullability, default, or constraint.
- **UNVERIFIED:** Object or attribute cannot be confirmed due to privilege or visibility limits.
- **REQUIRES USER DECISION:** Finding requires project owner sign-off.

### Current Status of Baseline Knowledge:

| Category / Object | Historical Phase 06 Observation | Phase 15 Live Status | Classification |
|---|---|---|:---:|
| **11 Application Tables** (`users`, `trends`, ..., `saved_trends`) | Not visible in `public` schema. | Not yet queried in Phase 15. | **UNVERIFIED (PENDING INSPECTION)** |
| **113 Application Columns** | Not visible in `public` schema. | Not yet queried in Phase 15. | **UNVERIFIED (PENDING INSPECTION)** |
| **12 Application Indexes** (`ix_*`) | Not visible in `public` schema. | Not yet queried in Phase 15. | **UNVERIFIED (PENDING INSPECTION)** |
| **11 Table RLS Statements** | Not visible (tables absent). | Not yet queried in Phase 15. | **UNVERIFIED (PENDING INSPECTION)** |
| **Storage Buckets** (`trend-images`, `collections`, `user-uploads`) | Zero bucket rows visible. | Not yet queried in Phase 15. | **UNVERIFIED (PENDING INSPECTION)** |
| **Extension `uuid-ossp`** | Installed in cluster. | Not yet queried in Phase 15. | **UNVERIFIED (PENDING INSPECTION)** |
| **Migration History Ledger** | No ledger table visible. | Not yet queried in Phase 15. | **NO RECOGNIZED MIGRATION LEDGER VISIBLE (HISTORICAL)** |

*(Note: "NO RECOGNIZED MIGRATION LEDGER VISIBLE" accurately reflects that no recognized migration table was found in Phase 06. It does not prove that the cluster is completely empty or that unrecorded DDL has never been run).*

---

## 6. Pre-Connection Report for Authorization

Before initiating any remote connection, the following operational parameters are established:

1. **Sanitized Target Host:** `aws-0-ap-northeast-1.pooler.supabase.com` (Port 6543) / `db.[REDACTED-20-CHAR-REF].supabase.co` (Port 5432).
2. **Connection Method:** Standalone script `inspect_supabase_readonly.py` via psycopg 3 over TLS (`sslmode=require`).
3. **Database Role:** `postgres.[REDACTED-20-CHAR-REF]`.
4. **Read-Only Enforcement:** `BEGIN READ ONLY;` + `current_setting('transaction_read_only') == 'on'` verification + unconditional `ROLLBACK;`.
5. **Data Protection:** Zero queries against user rows, passwords, or image blobs. System catalog queries only.
6. **Remaining Blockers:** None locally. The script is verified safe. Only user authorization to initiate the connection is required.

---

## 7. Safety Confirmation & Audit Summary

1. **Inspection Script Safety:** [`inspect_supabase_readonly.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/inspect_supabase_readonly.py) has been audited and confirmed safe to run under explicit read-only transaction boundaries.
2. **Cloud Resources:** Zero cloud resources, roles, tables, or storage buckets were modified or provisioned.
3. **Remote Connections:** **NO REMOTE DATABASE CONNECTION WAS INITIATED IN THIS STEP.**
