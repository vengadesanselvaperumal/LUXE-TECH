# LUXE.TECH — Phase 16: Database Permissions and RLS Design

**Document Location:** `supabase/proposals/PHASE_16_DATABASE_PERMISSIONS_AND_RLS_DESIGN.md`  
**Status:** APPROVED ARCHITECTURAL SPECIFICATION  
**Target:** Dedicated LUXE.TECH Supabase Project & FastAPI Backend Runtime  
**Author:** LUXE.TECH Senior Backend & Database Security Engineering  
**Date:** October 10, 2026  

---

## 1. Context and Problem Statement

LUXE.TECH operates a decoupled architecture consisting of:
- **Backend Service:** Standalone Python FastAPI application utilizing SQLAlchemy ORM.
- **Identity & Authentication:** Application-managed JWT tokens (HS256) signed with server-side `SECRET_KEY`, referencing user accounts stored in `public.users`.
- **Database Layer:** Supabase managed PostgreSQL with an auto-generated PostgREST REST API and a multi-tenant connection pooler (PgBouncer in transaction mode).

### 1.1 The RLS Default-Deny Lockout Problem
Under the PostgreSQL security model:
1. When Row Level Security is enabled on a table (`ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`), all queries executed by non-owner roles lacking `BYPASSRLS` are subject to active RLS policies.
2. If **zero policies** are defined, PostgreSQL enforces **default-deny**: every `SELECT`, `INSERT`, `UPDATE`, and `DELETE` operation executed by an unprivileged runtime role returns zero rows or errors.
3. Ordinary DML permissions (`GRANT SELECT, INSERT... ON ALL TABLES TO luxe_app_user`) do **not** override RLS default-deny.

### 1.2 The Custom JWT vs. Supabase Auth Disconnect
1. Supabase's built-in RLS documentation relies on `auth.uid()` and `auth.role()`, which extract user identity claims from GoTrue JWTs provided in the `Authorization: Bearer <token>` header.
2. LUXE.TECH issues custom application JWTs that are verified by FastAPI, not GoTrue. PostgreSQL and PostgREST evaluate `auth.uid()` as `NULL` for all LUXE.TECH connections.
3. Writing database policies that check `auth.uid() = user_id` would lock out all application queries.

---

## 2. Evaluation and Rejection of Alternative Designs

| Alternative Design | Core Mechanism | Reason for Rejection |
|---|---|---|
| **Runtime Superuser Account** | Backend connects directly as `postgres` or administrative superuser. | **Severe security risk:** Bypasses RLS cluster-wide, holds full DDL authority (`DROP TABLE`, `TRUNCATE`), and increases blast radius exponentially if credentials leak. |
| **`BYPASSRLS` Attribute Grant** | `ALTER ROLE luxe_app_user WITH BYPASSRLS;` | **Violates least privilege:** Completely eliminates database-level defense-in-depth across the entire PostgreSQL cluster. |
| **Table Ownership for Runtime Role** | `ALTER TABLE public.<table> OWNER TO luxe_app_user;` | **Dangerous privilege escalation:** Table owners bypass RLS on their tables and hold DDL modification powers. |
| **Transaction-Scoped Context (`SET LOCAL`)** | FastAPI injects `SET LOCAL request.jwt.claim.sub = :uid` per transaction. | **High operational & leakage risk:** On Supabase Transaction Pooler (port 6543), unhandled exceptions or autocommit queries can leak GUC session context across clients sharing a connection. Also breaks unauthenticated public catalog reads. |
| **Permissive PostgREST Roles** | Granting `SELECT` to `anon` and `authenticated` roles. | **Critical data leakage:** Allows anonymous internet users to query `https://<ref>.supabase.co/rest/v1/users` directly, scraping email addresses and user data. |

---

## 3. The Approved Solution: Least-Privilege Role + Explicit Policies

The approved architecture implements **Option 1: Explicit Application Runtime Policies** combined with **PostgREST Fail-Closed Revocation**.

### 3.1 Provisioning the Dedicated Runtime Role (`luxe_app_user`)
The runtime account is strictly sandboxed with no administrative capabilities:
```sql
CREATE ROLE luxe_app_user WITH
    LOGIN
    PASSWORD '<high_entropy_secret>'
    NOSUPERUSER
    NOCREATEDB
    NOREPLICATION
    NOBYPASSRLS;

-- Grant schema usage and standard DML only:
GRANT USAGE ON SCHEMA public TO luxe_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO luxe_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO luxe_app_user;
```

### 3.2 Locking Down the PostgREST Gateway (Fail-Closed Perimeter)
To prevent unauthorized direct queries to Supabase's auto-generated REST API, all privileges on application tables are explicitly revoked from public roles:
```sql
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM anon, authenticated;
```
Because no RLS policies are defined for `anon` or `authenticated`, any attempt to access `https://<ref>.supabase.co/rest/v1/...` returns empty sets or HTTP 401/403.

### 3.3 Enabling RLS with Explicit Policies for `luxe_app_user`
All 11 application tables have Row Level Security enabled. A single explicit, permissive policy is granted exclusively to `luxe_app_user` on each table:
```sql
-- Pattern applied to all 11 tables:
ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;

CREATE POLICY app_runtime_all ON public.<table>
    FOR ALL
    TO luxe_app_user
    USING (true)
    WITH CHECK (true);
```

---

## 4. Mapping to FastAPI Access Patterns

FastAPI serves as the secure application gateway, handling all authentication, authorization, and data filtering before queries reach PostgreSQL:

```mermaid
flowchart LR
    Client["Client Browser"] -->|HTTP Request| FastAPI["FastAPI Gateway"]
    FastAPI -->|1. JWT Auth Verification| AuthCheck["get_current_user / get_privileged_user"]
    AuthCheck -->|2. Tenant / Scope Filter| QueryGen["SQLAlchemy Query (user_id filter)"]
    QueryGen -->|3. Pooler Connection (luxe_app_user)| Postgres["Supabase PostgreSQL (Port 6543)"]
    Postgres -->|4. RLS Policy Checks luxe_app_user| TableData["Table Rows"]
    Client -.->|Direct PostgREST Attempt| SupabaseAPI["Supabase REST API"]
    SupabaseAPI -.->|REVOKE ALL + 0 Policies| Blocked["HTTP 401/403 / [] (Fail-Closed)"]
```

### 4.1 Public Catalog Reads
- **Endpoints:** `GET /api/trends`, `GET /api/trends/{slug}`, `GET /api/products`, `GET /api/retail`, `GET /api/dashboard`.
- **Flow:** Clients access public catalog data without authentication headers.
- **Database Execution:** FastAPI queries execute under `luxe_app_user`. The policy `app_runtime_all` permits `SELECT` operations. No user context is required.

### 4.2 Authenticated Personal Operations
- **Endpoints:** `POST /api/trends/{id}/save`, `GET /api/trends/saved`, `POST /api/images/analyze`.
- **Flow:** Request must include `Authorization: Bearer <custom_jwt>`.
- **FastAPI Enforcement:** `get_current_user` extracts `sub` (user UUID). Queries filter explicitly: `query(SavedTrend).filter(SavedTrend.user_id == current_user["id"])`.
- **Database Execution:** Queries execute under `luxe_app_user`. The policy allows execution, while the application enforces strict tenant isolation.

### 4.3 Privileged Catalog Mutations
- **Endpoints:** `POST /api/trends`, `POST /api/collections/generate`, `POST /api/products/generate`, `POST /api/forecast/{trend_id}`, `POST /api/prophecy/{trend_id}`.
- **FastAPI Enforcement:** Enforces `get_privileged_user` dependency: checks `current_user["role"] in {"admin", "lead_analyst"}`. Returns `HTTP 403 Forbidden` for standard users.
- **Database Execution:** Permitted under `luxe_app_user`.

---

## 5. Storage Security Architecture Separation

Storage bucket management is **strictly decoupled** from application table creation:
1. **Public Catalog Buckets (`trend-images`, `collections`):**
   - Configured with `public = true`, `file_size_limit = 10485760` (10 MB), and image MIME whitelist (`image/jpeg`, `image/png`, `image/webp`).
   - Read access via direct CDN URLs; write access restricted to backend service key.
2. **Private User Upload Bucket (`user-uploads`):**
   - Configured with `public = false`, `file_size_limit = 10485760` (10 MB), and image MIME whitelist.
   - Zero public read policies. Access requires temporary signed URLs (3600-second expiration) generated server-side.
   - Storage paths are namespaced by user ID (`storage_path = '{user_id}/{uuid}_{filename}'`).

---

## 6. Summary of Security Invariants

| Security Dimension | Enforcement Mechanism | Guarantees |
|---|---|---|
| **External PostgREST Isolation** | `REVOKE ALL` + 0 RLS policies for `anon`/`authenticated` | Direct Supabase REST API exposes zero application data. |
| **Backend Least Privilege** | `luxe_app_user` created with `NOSUPERUSER NOCREATEDB NOREPLICATION NOBYPASSRLS` | Application cannot execute DDL, drop tables, or bypass RLS cluster-wide. |
| **Connection Pooler Stability** | Stateless policies (`USING (true)`) without `SET LOCAL` | Zero risk of connection state pollution across PgBouncer pooled connections. |
| **Multi-Tenant Isolation** | FastAPI application layer (`get_current_user`, `user_id` filtering) | User bookmarks and uploads are strictly isolated to the authenticated owner. |
| **Upload Protection** | Bounded streaming read (10 MB cap), MIME validation, magic byte & Pillow decoding | Mitigates memory exhaustion DoS and malicious file injection. |

