# LUXE.TECH — Phase 14: Pre-Deployment Verification Checklist

**Document Location:** `supabase/proposals/PHASE_14_PREDEPLOYMENT_CHECKLIST.md`  
**Status:** BINDING DEPLOYMENT GATEWAY  
**Target Architecture:** FastAPI Standalone Application + Supabase Managed PostgreSQL Cluster  
**Scope:** Pre-flight checks, migration execution, RLS validation, storage provisioning, smoke testing, and abort protocol.  
**Date:** October 10, 2026  

---

## Deployment Gateway Overview

This checklist defines the rigorous sequence of verification gates required before, during, and after deploying the LUXE.TECH database schema to the dedicated Supabase project.

> [!CAUTION]
> **STRICT EXECUTION RULE:**
> No remote database connection, SQL command, bucket creation, or environment configuration change may be executed until every item in **Phase A** and **Phase B** has been checked and signed off.

---

## Phase A: Pre-Flight Governance & Environment Verification

| Step | Check Item | Verification Command / Evidence | Status | Sign-Off |
|:---:|---|---|:---:|:---:|
| **A.1** | **Offline Test Suite Passing** | Full backend test suite passing (42/42 tests passing, including 15 API security tests). | `[PASS]` | Verified Phase 11 |
| **A.2** | **Static Schema Parity Verified** | Static validator confirms 11 tables, 113 columns, 12 indexes, and 11 RLS statements match SQLAlchemy ORM. | `[PASS]` | Verified Phase 14 |
| **A.3** | **Zero Destructive Commands** | Migration candidate contains zero `DROP TABLE`, `TRUNCATE`, or `CASCADE` commands in executable DDL. | `[PASS]` | Verified Phase 14 |
| **A.4** | **Secret Isolation & Hygiene** | No passwords, service keys, JWT secrets, or DB URLs committed to git history or output to logs. | `[PASS]` | Verified |
| **A.5** | **Architecture Decision Signed** | Phase 14 RLS ADR approved: Option 1 (explicit `luxe_app_user` runtime policies). | `[PASS]` | Approved Phase 14 |

---

## Phase B: Supabase Remote Project Baseline Inspection (Manual / Interactive)

| Step | Check Item | Verification Method / Requirement | Status | Sign-Off |
|:---:|---|---|:---:|:---:|
| **B.1** | **Target Project Identity** | Verify Supabase project reference matches the dedicated LUXE.TECH project (not old/unrelated projects). | `[PENDING]` | Pre-deployment gate |
| **B.2** | **Public Schema Clean State** | Query remote DB: `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public';`<br>Must return `0` application tables. | `[PENDING]` | Pre-deployment gate |
| **B.3** | **Automated Backup / PITR Verification** | Confirm in Supabase Dashboard (Settings -> Backups) that automated snapshots or Point-In-Time Recovery (PITR) are enabled. | `[PENDING]` | Pre-deployment gate |
| **B.4** | **Connection Mode Selection** | For FastAPI SQLAlchemy pool, select **Transaction Pooler (Port 6543)** with `prepare_threshold=None` (or direct Port 5432 for migrations). | `[PENDING]` | Pre-deployment gate |

---

## Phase C: Database Roles & Runtime Security Provisioning

| Step | Action Item | SQL / Dashboard Command | Status | Sign-Off |
|:---:|---|---|:---:|:---:|
| **C.1** | **Create Runtime Role** | Execute via administrative connection (`postgres`):<br>`CREATE ROLE luxe_app_user WITH LOGIN PASSWORD '<runtime_password>' NOSUPERUSER NOCREATEDB NOREPLICATION NOBYPASSRLS;` | `[PENDING]` | Migration step |
| **C.2** | **Grant Schema Usage** | `GRANT USAGE ON SCHEMA public TO luxe_app_user;` | `[PENDING]` | Migration step |
| **C.3** | **Grant DML Operations** | `GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO luxe_app_user;`<br>`ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO luxe_app_user;` | `[PENDING]` | Migration step |
| **C.4** | **Verify Least Privilege** | Query `pg_roles` to verify `luxe_app_user` has `rolsuper=false`, `rolcreaterole=false`, `rolcreatedb=false`, `rolbypassrls=false`. | `[PENDING]` | Migration step |

---

## Phase D: Canonical Migration Execution

| Step | Action Item | Execution Method | Status | Sign-Off |
|:---:|---|---|:---:|:---:|
| **D.1** | **Open Transaction** | Execute migration within an atomic transaction block: `BEGIN;` | `[PENDING]` | Execution step |
| **D.2** | **Apply Core Tables DDL** | Execute `supabase/proposals/luxe_phase12_canonical_candidate_migration.sql` lines 20–237 (11 tables, 113 columns, 12 indexes). | `[PENDING]` | Execution step |
| **D.3** | **Enable RLS on All Tables** | Execute `ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;` on all 11 tables. | `[PENDING]` | Execution step |
| **D.4** | **Apply Runtime Policies (Option 1)** | Execute `CREATE POLICY app_runtime_all ON public.<table> FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);` on all 11 tables. | `[PENDING]` | Execution step |
| **D.5** | **Revoke Public PostgREST Access** | Execute:<br>`REVOKE ALL ON public.users FROM anon, authenticated;`<br>`REVOKE ALL ON public.saved_trends FROM anon, authenticated;` | `[PENDING]` | Execution step |
| **D.6** | **Record Migration in Ledger** | Record migration execution in schema version tracking table. | `[PENDING]` | Execution step |
| **D.7** | **Commit Transaction** | Execute `COMMIT;` (or `ROLLBACK;` if any error occurs). | `[PENDING]` | Execution step |

---

## Phase E: Post-Migration DDL & Security Audit

| Step | Audit Item | Verification Query / Command | Expected Result | Status |
|:---:|---|---|---|:---:|
| **E.1** | **Table Count** | `SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE';` | Exactly `11` tables | `[PENDING]` |
| **E.2** | **RLS Activation** | `SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname = 'public';` | All 11 tables have `rowsecurity = true` | `[PENDING]` |
| **E.3** | **Policy Assignment** | `SELECT tablename, policyname, roles FROM pg_policies WHERE schemaname = 'public';` | 11 policies named `app_runtime_all` targeting `{luxe_app_user}` | `[PENDING]` |
| **E.4** | **Index Count** | `SELECT count(*) FROM pg_indexes WHERE schemaname = 'public' AND indexname LIKE 'ix_%';` | Exactly `12` indexes | `[PENDING]` |
| **E.5** | **PostgREST Fail-Closed Test** | `curl -s -H "apikey: <ANON_KEY>" https://<project-ref>.supabase.co/rest/v1/users` | Returns `[]` or `401/403` (zero data exposed) | `[PENDING]` |

---

## Phase F: Storage Bucket Provisioning & Access Control

| Bucket Name | Visibility | File Size Limit | Allowed MIME Types | Access Protocol | Status |
|---|---|---|---|---|:---:|
| `trend-images` | **Public** | 10 MB (`10485760` bytes) | `image/jpeg`, `image/png`, `image/webp` | Direct CDN URL for read; Backend service role for write | `[PENDING]` |
| `collections` | **Public** | 10 MB (`10485760` bytes) | `image/jpeg`, `image/png`, `image/webp` | Direct CDN URL for read; Backend service role for write | `[PENDING]` |
| `user-uploads` | **Private** | 10 MB (`10485760` bytes) | `image/jpeg`, `image/png`, `image/webp` | Signed URLs only (3600s expiration); Namespaced `{user_id}/...` | `[PENDING]` |

---

## Phase G: Runtime Connection & Application Smoke Testing

| Step | Smoke Test | Test Procedure | Expected Outcome | Status |
|:---:|---|---|---|:---:|
| **G.1** | **Backend Connection Switch** | Set `DATABASE_URL` to Supabase connection string using `luxe_app_user`. | Connection established over SSL. | `[PENDING]` |
| **G.2** | **Schema Integrity Check** | Run FastAPI startup; triggers `init_db()` in `database.py`. | No missing tables or columns detected; zero errors. | `[PENDING]` |
| **G.3** | **Seed Account Provisioning** | Seed baseline data via `database_seed.py`. | Tables populated with initial catalog data. | `[PENDING]` |
| **G.4** | **Admin Password Hardening** | Set salted PBKDF2 hash on `analyst@luxe.tech` and enforce `ALTER TABLE public.users ALTER COLUMN password_hash SET NOT NULL;`. | Password hash enforced; column is `NOT NULL`. | `[PENDING]` |
| **G.5** | **Public Catalog Read** | `GET /api/trends` via HTTP client. | Returns `HTTP 200` with trends catalog. Zero DB writes. | `[PENDING]` |
| **G.6** | **Auth Registration & Login** | `POST /api/auth/register` and `POST /api/auth/login`. | User created with role `"user"`; valid JWT returned. | `[PENDING]` |
| **G.7** | **Personal Upload Isolation** | `POST /api/images/analyze` with valid image under 10 MB. | Stored in private bucket under `{user_id}/...`; signed URL returned. | `[PENDING]` |
| **G.8** | **Privilege Escalation Block** | Standard user calls `POST /api/trends`. | Returns `HTTP 403 Forbidden`. | `[PENDING]` |
| **G.9** | **Rate Limiter Verification** | Burst requests to `/api/auth/login`. | Enforces 10 req/min limit without IP-spoofing bypass. | `[PENDING]` |

---

## Phase H: Abort & Emergency Recovery Protocol

### Protocol H.1: Day-0 Pre-Launch Abort (Empty Target Failure)
- **Condition:** An unexpected error occurs during Phase D migration execution on a fresh, unpopulated database.
- **Immediate Action:** The transaction is aborted via `ROLLBACK;`.
- **Manual Cleanup (if partial commits occurred outside transaction):**
  Because no production or user data exists, dropping the partial tables is permissible:
  ```sql
  -- EMERGENCY DAY-0 ABORT ONLY (ONLY PERMISSIBLE WHEN ZERO PRODUCTION DATA EXISTS)
  DROP TABLE IF EXISTS public.saved_trends CASCADE;
  DROP TABLE IF EXISTS public.prophecy CASCADE;
  DROP TABLE IF EXISTS public.forecasts CASCADE;
  DROP TABLE IF EXISTS public.retail_signals CASCADE;
  DROP TABLE IF EXISTS public.products CASCADE;
  DROP TABLE IF EXISTS public.collections CASCADE;
  DROP TABLE IF EXISTS public.images CASCADE;
  DROP TABLE IF EXISTS public.trend_dna CASCADE;
  DROP TABLE IF EXISTS public.trend_signals CASCADE;
  DROP TABLE IF EXISTS public.trends CASCADE;
  DROP TABLE IF EXISTS public.users CASCADE;
  ```
- **Post-Abort:** Fix the migration script error locally, verify offline, and re-run Phase A–D.

### Protocol H.2: Post-Launch Disaster Recovery (Production Data Exists)
> [!CAUTION]
> **STRICT BAN ON `DROP TABLE ... CASCADE` AFTER LAUNCH:**
> Once production data or real user accounts exist, destructive DDL (`DROP TABLE`, `TRUNCATE`, `DROP ... CASCADE`) is strictly forbidden under all circumstances.

- **Recovery Mechanism:**
  1. **Schema Defects:** Correct via forward-repair migration (`ALTER TABLE ... ADD/ALTER COLUMN`).
  2. **Data Corruption or Accidental Deletion:** Initiate Point-in-Time Recovery (PITR) to restore the PostgreSQL cluster to the nearest microsecond timestamp prior to the incident.
  3. **Disaster Snapshot Restore:** Restore from the latest daily automated Supabase snapshot into a secondary staging instance, verify data integrity, and execute cutover.

