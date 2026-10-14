# LUXE.TECH — Phase 20: Runtime Role Provisioning Readiness

**Report Location:** [`PHASE_20_RUNTIME_ROLE_READINESS.md`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/PHASE_20_RUNTIME_ROLE_READINESS.md)  
**Execution Mode:** STRICTLY LOCAL & OFFLINE (Zero remote database connections, zero SQL executions, zero credential exposure)  
**Date:** October 11, 2026  
**Auditor:** Senior Database & Application Security Migration Engineer  

---

## 1. Executive Summary

This report establishes the readiness and procedures for provisioning and operating the dedicated least-privilege backend runtime role: **`luxe_app_user`**.

In Phase 18, [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql) eliminated all executable placeholder passwords (`REPLACE_WITH_STRONG_PASSWORD`) and established an atomic pre-flight existence guard:
```sql
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'luxe_app_user') THEN
        RAISE EXCEPTION 'Prerequisite failed: Database role "luxe_app_user" does not exist. Please create the role with a secure password prior to executing this migration.';
    END IF;
END
$$;
```

This Phase 20 review inspects the connection pipeline, fallback behavior, provisioning protocol, credential safety, and pre-deployment testing without connecting to remote services or exposing secrets.

---

## 2. Backend Database Connection Selection & `luxe_app_user` Support

### 2.1 Connection Selection Architecture
The database connection configuration flows through two modules:

1. **Environment Loading ([`backend/app/config.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/config.py)):**
   * Uses `pydantic_settings.BaseSettings` reading from OS environment variables, then `.env`, and finally `../.env`.
   * Defines default `DATABASE_URL = "sqlite:///./backend/luxe_tech.db"`.
2. **Engine Creation ([`backend/app/database.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/database.py)):**
   * Reads `settings.DATABASE_URL`.
   * For SQLite: configures `connect_args = {"check_same_thread": False}` and creates directory paths.
   * For PostgreSQL: passes the connection string directly to `create_engine(db_url, connect_args=connect_args)`.
   * Uses `sessionmaker(autocommit=False, autoflush=False, bind=engine)` to vend `SessionLocal` sessions.

### 2.2 Support for `luxe_app_user`
* **Zero Code Changes Required:** SQLAlchemy and Psycopg natively parse standard PostgreSQL connection URIs containing `luxe_app_user`.
* **Direct Connection URI (Port 5432):**
  ```
  postgresql://luxe_app_user:<encoded_password>@db.<project_ref>.supabase.co:5432/postgres?sslmode=require
  ```
* **Supabase Transaction Pooler URI (Port 6543 / PgBouncer):**
  On Supabase, connections to port 6543 route through PgBouncer, which requires the username to specify the project tenant:
  ```
  postgresql://luxe_app_user.<project_ref>:<encoded_password>@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres?sslmode=require
  ```
* **Password Character Encoding:** If the password contains reserved URI characters (`:`, `@`, `/`, `?`, `#`, `[`, `]`, `%`, `&`, `+`), they must be percent-encoded using `urllib.parse.quote_plus()`. Using URL-safe alphanumeric tokens (`secrets.token_urlsafe(32)`) eliminates encoding hazards entirely.

---

## 3. Fallback Analysis: SQLite, `postgres`, and Privileged Roles

### 3.1 SQLite Fallback Behavior
* **When Active:** The backend falls back to SQLite **only** when `DATABASE_URL` is omitted, blank, or starts with `sqlite:`.
* **Absence of Silent Failure:** If `DATABASE_URL` is configured to PostgreSQL and the database is unreachable, bad credentials are provided, or network fails, **the backend does NOT fall back to SQLite**.
  - During application startup (`lifespan`), `init_db()` will raise an exception and immediately halt process initialization.
  - On the health check route ([`/api/health`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/main.py#L120-L151)), the failed connection raises an HTTP 503 (`Database is unavailable.`).

### 3.2 The Privileged `postgres` Role Hazard
* **Current Offline Configuration:** Inspection of `.env` revealed that the currently configured connection URI uses the administrative username (`postgres.<project_ref>`).
* **Privilege Exposure Risk:** If the application connects as `postgres`:
  - `postgres` on Supabase has `BYPASSRLS = true`.
  - All Row Level Security policies are completely bypassed at the database layer.
  - The application possesses full DDL capabilities (`DROP TABLE`, `ALTER TABLE`, `CREATE ROLE`), violating the principle of least privilege.
* **Lack of Runtime Assertion:** The application currently does not assert that `current_user != 'postgres'` in production. The transition to `luxe_app_user` must be explicitly verified before opening public traffic.

---

## 4. Secure Manual Provisioning Procedure for `luxe_app_user`

The creation of `luxe_app_user` must occur in an administrative, private context prior to executing [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql).

### 4.1 Execution Context
* **Platform:** Private Supabase SQL Editor session (logged in as project administrator).
* **Isolation:** Never execute in shared terminals, recorded scripts, or tracked migration files.

### 4.2 SQL Provisioning Commands
```sql
-- ============================================================================
-- RUNTIME ROLE PROVISIONING (PRIVATE OPERATOR SESSION ONLY)
-- Do NOT commit this statement with a real password into source control.
-- ============================================================================

-- 1. Create the dedicated least-privilege role
CREATE ROLE luxe_app_user WITH
    LOGIN
    PASSWORD '<HIGH_ENTROPY_PASSWORD>'
    NOSUPERUSER
    NOCREATEDB
    NOREPLICATION
    NOBYPASSRLS;

-- 2. Grant connection privilege to the target database
GRANT CONNECT ON DATABASE postgres TO luxe_app_user;
```

### 4.3 Idempotent Role Hardening (If Role Already Exists)
If the role already exists from an earlier setup, re-verify and harden its attributes:
```sql
ALTER ROLE luxe_app_user WITH
    LOGIN
    NOSUPERUSER
    NOCREATEDB
    NOREPLICATION
    NOBYPASSRLS;

-- Update password if needed:
ALTER ROLE luxe_app_user WITH PASSWORD '<HIGH_ENTROPY_PASSWORD>';
```

---

## 5. Local Password Generation and Storage Protocol

To prevent accidental exposure in chat, logs, source code, shell history, or Git, operators must adhere to this strict protocol:

### 5.1 Strong Password Generation
Generate a cryptographically random, high-entropy secret using Python's standard library `secrets` module:
```python
import secrets

# Generates a 43-character, ~256-bit entropy, URL-safe secret:
password = secrets.token_urlsafe(32)
print(password)
```
* **Advantages of `token_urlsafe`:** Contains only `A-Z`, `a-z`, `0-9`, `-`, `_`. Contains no `:`, `@`, `/`, `?`, `#`, or `%`, completely eliminating URL-encoding issues in connection strings.

### 5.2 Exposure Prevention Checklist
1. **Chat & LLM Prompts:** Never paste the generated password or full connection string into chat or prompts.
2. **Migration Files:** Never embed the password into SQL files staged under `supabase/migrations/` or `supabase/proposals/`.
3. **Shell History (`PSReadLine` / `.bash_history`):** Do not pass the password as an inline command-line flag (e.g. `psql -W <password>`). Inline flags are permanently logged to disk.
4. **Git Repository:** Store the secret exclusively in local `.env`. Verify that `.gitignore` contains:
   ```
   .env
   .env.*
   !.env.example
   ```
   *(Verified: `.gitignore` currently ignores `.env` and `.env.*`).*
5. **Application Logging:** Confirm application loggers do not print the connection URI. [`backend/app/main.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/main.py#L125-L127) only logs `type(exc).__name__` upon failure and extracts only `.hostname` for display.

---

## 6. Verification of Role Attributes and Connection Identity

Operators must verify role confinement without returning or exposing password hashes.

### 6.1 Role Confinement Verification Query
Run in the Supabase SQL Editor:
```sql
SELECT
    rolname,
    rolcanlogin,
    rolsuper,
    rolcreaterole,
    rolcreatedb,
    rolreplication,
    rolbypassrls
FROM pg_roles
WHERE rolname = 'luxe_app_user';
```

**Required Output:**
| Column | Expected Value | Security Rationale |
|---|:---:|---|
| `rolname` | `luxe_app_user` | Target runtime role |
| `rolcanlogin` | `true` | Allows FastAPI backend authentication |
| `rolsuper` | `false` | Zero superuser permissions |
| `rolcreaterole` | `false` | Cannot alter or create other database roles |
| `rolcreatedb` | `false` | Cannot create or drop databases |
| `rolreplication` | `false` | Cannot access replication streams |
| `rolbypassrls` | `false` | Bound by Row Level Security policies |

### 6.2 Connection Identity Verification Query
To verify which identity an active connection is operating under:
```sql
SELECT current_user, session_user, current_setting('is_superuser');
```

**Required Output:**
* `current_user`: `luxe_app_user`
* `session_user`: `luxe_app_user`
* `is_superuser`: `off`

---

## 7. Pre-Migration Deployment Testing Strategy

Before deploying [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql), operators must execute these non-destructive tests:

### 7.1 Connection Probe
* Connect as `luxe_app_user` and execute:
  ```sql
  SELECT 1;
  ```
  Confirms valid credentials, SSL negotiation, and network accessibility.

### 7.2 Application Fail-Fast Guard Test (Pre-Migration)
* Configure `DATABASE_URL` with `luxe_app_user`.
* Attempt to boot the FastAPI application.
* **Expected Result:**
  [`backend/app/database.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/database.py#L270-L308) (`init_db()`) runs `inspector.get_table_names()`.
  Detects that the 11 tables are missing, raises a `RuntimeError`, and **aborts startup immediately**:
  ```
  RuntimeError: PostgreSQL schema is incomplete; no tables were created or changed.
  Apply and verify the reviewed Supabase migrations first (missing tables: collections,
  forecasts, images, products, prophecy, retail_signals, saved_trends, trend_dna,
  trend_signals, trends, users).
  ```
  *Proves that the backend refuses to serve traffic against an un-migrated schema and refuses to auto-create incomplete tables.*

### 7.3 Post-Migration Verification
* Once [`luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql) is executed:
  1. `init_db()` completes without errors.
  2. Automatic demo seeding is bypassed (`engine.dialect.name != "sqlite"`).
  3. `GET /api/health` returns HTTP 200:
     ```json
     {
       "success": true,
       "data": {
         "status": "healthy",
         "database_backend": "postgresql",
         "database_connected": true,
         "supabase_postgres_configured": true,
         "supabase_postgres_connected": true
       }
     }
     ```

---

## 8. Remaining Security Risks and Defense-in-Depth Analysis

### 8.1 Broad Runtime RLS Policies (`USING (true) WITH CHECK (true)`)
* **Risk Description:** Database policies named `app_runtime_all` grant `luxe_app_user` uniform DML access across all rows on all 11 tables. PostgreSQL does **not** evaluate per-user row ownership filters at the database engine level for `luxe_app_user`.
* **Tenant Isolation Locus:** Row-level multi-tenant isolation rests **100% on the FastAPI application layer** (e.g. `SavedTrend.user_id == current_user["id"]` in [`trends.py`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/app/routers/trends.py#L180-L210)).
* **Impact of Application Vulnerabilities:** If an application route contains a bug omitting `user_id` validation, or if SQL injection occurs, `luxe_app_user` can read or modify data belonging to any tenant.
* **Why This Architecture Was Adopted:** In Phase 14, Option 1 was selected because LUXE.TECH uses a standalone FastAPI custom JWT implementation (HS256) rather than Supabase Auth (`auth.users`). PostgreSQL has no native session context for LUXE.TECH users without custom connection-hook session variables (`SET LOCAL luxe.current_user_id`).
* **Compensating Controls:**
  - Automated test suite enforces cross-user bookmark isolation ([`backend/tests/test_api_security.py::test_cross_user_isolation_on_saved_trends`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/backend/tests/test_api_security.py#L125)).
  - Storage uploads are namespaced by user ID (`{user_id}/{uuid}_{filename}`).
  - Strict parameterization and ORM abstraction eliminate raw SQL concatenation.

### 8.2 PostgREST Public Exposure Surface
* PostgREST public exposure is prevented via explicit `REVOKE ALL ON TABLE ... FROM anon, authenticated;` in the migration.
* If a future migration creates a new table without revoking permissions, PostgREST default schema grants could expose it. PostgREST fail-closed verification must remain part of all future migration checklists.

### 8.3 Connection Pooler Session Mode vs Transaction Mode
* When using Supabase port 6543 (transaction pooling), session-level state (`SET session ...`, `LISTEN/NOTIFY`, temporary tables) is prohibited.
* SQLAlchemy connection pooling must be configured appropriately (e.g. `NullPool` or standard client pooling with `pool_pre_ping=True`).

---

## 9. Summary of Offline Execution Checks

The following automated offline checks were executed:

| Check Item | Script / Method | Result | Evidence |
|---|---|:---:|---|
| **Default Settings Parsing** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | Default falls back to local SQLite |
| **`luxe_app_user` URI Parsing** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | SQLAlchemy/urlparse parses `luxe_app_user` correctly |
| **Privileged Role Detection** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | `postgres` correctly identified as privileged role |
| **Pre-Migration Rejection Guard** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | `init_db()` raises `RuntimeError` on empty PostgreSQL |
| **Partial Schema Rejection Guard** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | `init_db()` raises `RuntimeError` on partial tables |
| **Complete Schema Acceptance** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | `init_db()` passes cleanly on 11 tables / 113 cols |
| **URL-Safe Encoding Roundtrip** | `scratch/test_phase20_runtime_readiness.py` | **PASS** | Percent-encoding verified without character loss |
| **Full Pytest Security Suite** | `pytest backend/tests` | **PASS** | 42 passed, 0 failed in 32.04s |

---

## 10. Conclusion and Next Operator Steps

1. **Role Provisioning Gate:** The human operator must execute the `CREATE ROLE luxe_app_user` block in the private Supabase SQL Editor.
2. **Migration Execution Gate:** Once `luxe_app_user` is verified, execute [`supabase/proposals/luxe_phase18_hardened_first_install.sql`](file:///c:/Users/Lenovo/Downloads/FORCASTING%20WEBSITE/supabase/proposals/luxe_phase18_hardened_first_install.sql).
3. **Configuration Transition Gate:** Update `DATABASE_URL` in `.env` to reference `luxe_app_user` (or `luxe_app_user.<project_ref>` if using pooler port 6543) instead of `postgres`.
4. **Boot & Verify:** Boot FastAPI and verify that `GET /api/health` reports status `healthy`.

