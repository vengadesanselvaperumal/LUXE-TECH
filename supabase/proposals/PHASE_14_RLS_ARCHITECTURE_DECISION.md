# LUXE.TECH — Phase 14: Row Level Security (RLS) Architecture Decision

**Document Location:** `supabase/proposals/PHASE_14_RLS_ARCHITECTURE_DECISION.md`  
**Status:** ARCHITECTURAL DECISION RECORD (ADR) — APPROVED SPECIFICATION  
**Target Architecture:** FastAPI Standalone Application + Supabase Managed PostgreSQL Cluster  
**Author:** LUXE.TECH Senior Backend & Database Security Engineering  
**Date:** October 10, 2026  

---

## 1. Context and Problem Statement

LUXE.TECH is a Fashion Intelligence and Forecasting Platform with a decoupled architecture:
- **Backend Runtime:** A standalone Python FastAPI service using SQLAlchemy ORM.
- **Authentication:** Custom JWT tokens signed by the FastAPI backend using `HS256` and `SECRET_KEY`, referencing user records in `public.users`.
- **Database:** Supabase managed PostgreSQL with a built-in PostgREST HTTP gateway and multi-tenant connection pooler (PgBouncer in transaction mode).

In Phase 12, canonical schema candidate migration `supabase/proposals/luxe_phase12_canonical_candidate_migration.sql` was authored. It enables Row Level Security (RLS) across all 11 application tables (`ALTER TABLE public.<table> ENABLE ROW LEVEL SECURITY;`).

In Phase 13, independent security analysis revealed the **PostgreSQL Default-Deny Lockout Trap**:
> Under PostgreSQL specification, when Row Level Security is enabled on a table, all queries executed by non-owner roles lacking `BYPASSRLS` are subject to active RLS policies. If **zero policies** are defined, PostgreSQL enforces default-deny: all `SELECT`, `INSERT`, `UPDATE`, and `DELETE` operations from unprivileged roles return zero rows or fail.

Because standard DML grants (`GRANT SELECT, INSERT... ON ALL TABLES TO luxe_app_user`) do **not** bypass RLS, connecting the FastAPI backend via a dedicated least-privilege role (`luxe_app_user`) while RLS is enabled with zero policies will completely break the application upon deployment.

This document formally evaluates the available architectural options and records the binding decision for LUXE.TECH.

---

## 2. Evaluation of Architectural Options

### Option 1: Explicit `luxe_app_user` Policies Granting Backend-Wide Row Access

#### Description
The database defines an explicit, permissive RLS policy on each table scoped strictly to the backend runtime role `luxe_app_user`:
```sql
CREATE POLICY app_runtime_all ON public.<table>
    FOR ALL
    TO luxe_app_user
    USING (true)
    WITH CHECK (true);
```
Under this model, the database delegates row-level tenant filtering and authorization to the FastAPI application layer, while maintaining a strict fail-closed boundary against external direct database access.

#### Evaluation Against Key Criteria
1. **PostgREST Default-Deny Behavior:**
   - External requests arriving through Supabase's PostgREST gateway execute as `anon` or `authenticated` (Supabase Auth role).
   - Because no policies exist for `anon` or `authenticated`, PostgREST unconditionally returns empty arrays (`[]`) or authorization errors.
   - External attackers attempting to query `https://<project-ref>.supabase.co/rest/v1/users` or `/trends` are blocked by default.
2. **Connection Pooling & Context Leakage Risk:**
   - **Zero risk.** Queries executed by `luxe_app_user` do not set or rely on connection-level GUC parameters (`SET LOCAL`).
   - Completely safe across Supabase Transaction Pooler (PgBouncer on port 6543). No session pollution can occur between pooled connections.
3. **Role Attributes & Least Privilege:**
   - `luxe_app_user` is provisioned with `NOSUPERUSER`, `NOCREATEDB`, `NOREPLICATION`, and `NOBYPASSRLS`.
   - `luxe_app_user` possesses only DML privileges (`SELECT, INSERT, UPDATE, DELETE`) on `public` tables. It cannot perform destructive DDL (`DROP TABLE`, `ALTER TABLE`, `TRUNCATE`).
   - Does not grant global bypass rights; access is explicitly governed by the targeted table policies.
4. **FastAPI & SQLAlchemy Complexity:**
   - **Zero code changes required.** SQLAlchemy sessions and existing queries operate normally without middleware, hooks, or connection-level state injection.
   - Application-layer authorization (enforced via `get_current_user`, `get_privileged_user`, and explicit `user_id` filtering) remains the single source of truth for business logic.
5. **Public Catalog Support:**
   - Public discovery routes (`GET /api/trends`, `GET /api/products`, `GET /api/retail`) operate cleanly because queries from the backend execute under `luxe_app_user` without requiring a synthetic anonymous user identity.

---

### Option 2: Per-User PostgreSQL RLS Policies Using Transaction-Scoped User Identity Context

#### Description
The database enforces tenant isolation in PostgreSQL SQL policies using session parameters (GUC variables):
```sql
CREATE POLICY user_isolation_saved_trends ON public.saved_trends
    FOR ALL
    TO luxe_app_user
    USING (user_id = current_setting('luxe.current_user_id', true))
    WITH CHECK (user_id = current_setting('luxe.current_user_id', true));
```
In FastAPI, every database transaction must inject the authenticated user ID before executing any query:
```python
db.execute(text("SET LOCAL luxe.current_user_id = :uid"), {"uid": current_user["id"]})
```

#### Evaluation Against Key Criteria
1. **PostgREST Default-Deny Behavior:**
   - Maintains fail-closed behavior for `anon` and `authenticated`.
2. **Connection Pooling & Context Leakage Risk:**
   - **CRITICAL RISK.** Supabase uses PgBouncer in transaction pooling mode.
   - Although `SET LOCAL` is cleared on `COMMIT` or `ROLLBACK`, any query executed outside an explicit transaction block, or any unhandled exception that bypasses clean rollback, can leave the GUC variable assigned on the pooled connection.
   - Subsequent requests sharing that pooled connection may inherit the previous user's identity, causing catastrophic cross-tenant data leaks.
3. **Role Attributes & Least Privilege:**
   - Uses `NOBYPASSRLS`, which is positive from a role attribute standpoint.
4. **FastAPI & SQLAlchemy Complexity:**
   - **EXTREMELY HIGH.**
   - Every single endpoint, dependency, and background job in FastAPI must be wrapped in transactional GUC setter logic.
   - Public discovery endpoints (`GET /api/trends`) have no user context. Policies must incorporate complex conditional logic (`OR current_setting('luxe.current_user_id', true) IS NULL`) which easily introduces bypass vulnerabilities.
   - Background tasks, automated analytics, seed scripts, and CLI utilities fail unless they synthesize a user context.
5. **Performance Overhead:**
   - Requires an additional round-trip `SET LOCAL` SQL command per transaction, increasing latency on high-frequency endpoints.

---

### Option 3: Trusted Backend Role with Elevated Attributes (Table Owner or `BYPASSRLS`)

#### Description
The FastAPI backend connects using a database role that either:
1. Owns all application tables (`ALTER TABLE ... OWNER TO luxe_app_user`), OR
2. Possesses the PostgreSQL `BYPASSRLS` attribute (`ALTER ROLE luxe_app_user WITH BYPASSRLS;`).

#### Evaluation Against Key Criteria
1. **PostgREST Default-Deny Behavior:**
   - RLS is still enabled for other roles, so PostgREST `anon` and `authenticated` roles remain blocked.
2. **Connection Pooling & Context Leakage Risk:**
   - Zero risk (no GUC state).
3. **Role Attributes & Least Privilege:**
   - **MAJOR VIOLATION OF LEAST PRIVILEGE.**
   - If `luxe_app_user` is given `BYPASSRLS`, the role bypasses all RLS policies across the entire database cluster, eliminating defense-in-depth. If application credentials leak, the attacker bypasses all database-level security barriers.
   - If `luxe_app_user` is table owner, it possesses destructive DDL privileges (`DROP TABLE`, `TRUNCATE`, `ALTER TABLE`), allowing SQL injection vulnerabilities to alter the schema or drop tables.
4. **FastAPI & SQLAlchemy Complexity:**
   - Low code complexity, but operationally fragile and violates strict database security standards.

---

## 3. Comprehensive Comparison Matrix

| Evaluation Dimension | Option 1: Explicit `luxe_app_user` Policies | Option 2: Transaction-Scoped Context (`SET LOCAL`) | Option 3: Elevated Attributes (`BYPASSRLS` / Owner) |
|---|---|---|---|
| **PostgREST Fail-Closed Defense** | **YES** (100% blocked for external callers) | **YES** (100% blocked for external callers) | **YES** (100% blocked for external callers) |
| **Transaction Pooler Safety (PgBouncer)** | **PERFECT** (Stateless, 0% leakage risk) | **HIGH RISK** (Session pollution possible) | **PERFECT** (Stateless, 0% leakage risk) |
| **Role Least Privilege** | **EXCELLENT** (`NOBYPASSRLS`, DML only, no DDL) | **EXCELLENT** (`NOBYPASSRLS`, DML only) | **POOR** (Elevated bypass or DDL ownership) |
| **Public Catalog Reads** | **SEAMLESS** (Direct read without mock identity) | **COMPLEX** (Requires fallback / NULL handling) | **SEAMLESS** (Direct read) |
| **SQLAlchemy / FastAPI Impact** | **ZERO** (Existing code works unchanged) | **HEAVY** (Session interceptors on all routes) | **ZERO** (Existing code works unchanged) |
| **Operational Overhead** | **LOW** (1 policy per table in migration DDL) | **VERY HIGH** (Complex debugging and testing) | **LOW** (Role attribute assignment) |
| **Defense-in-Depth** | **HIGH** (RLS locks gateway; app isolates users) | **VERY HIGH** (Database verifies user ID) | **LOW** (Database provides no secondary barrier) |

---

## 4. Formal Recommendation and Architectural Decision

### Decision: Adopt Option 1 (Explicit `luxe_app_user` Runtime Policies)

**Rationale:**
1. **Matches Standalone Architecture:** LUXE.TECH operates an independent FastAPI backend with custom JWT token validation. Supabase Auth is not used for client sessions. Option 1 recognizes this architecture cleanly without forcing artificial Supabase Auth abstractions into the database.
2. **Guarantees Transaction Pooler Stability:** Option 1 is 100% immune to connection pool state leakage on Supabase port 6543.
3. **Maintains Complete PostgREST Isolation:** External clients calling PostgREST directly cannot access any table data because `anon` and `authenticated` roles have zero grants and zero policies.
4. **Enforces True Least Privilege:** The runtime role `luxe_app_user` has strictly DML privileges (`SELECT`, `INSERT`, `UPDATE`, `DELETE`) with `NOBYPASSRLS` and no DDL rights.

### SQL Specification for Policy Implementation

The candidate migration or deployment script must include the following policy definitions for all 11 tables:

```sql
-- Grant runtime DML permissions
GRANT USAGE ON SCHEMA public TO luxe_app_user;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO luxe_app_user;

-- Create explicit runtime policies on all 11 tables
CREATE POLICY app_runtime_all ON public.users FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.trends FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.trend_signals FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.trend_dna FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.images FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.collections FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.products FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.retail_signals FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.forecasts FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.prophecy FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
CREATE POLICY app_runtime_all ON public.saved_trends FOR ALL TO luxe_app_user USING (true) WITH CHECK (true);
```

---

## 5. Unresolved Security Decisions Requiring User Approval

Prior to production deployment, the following governance decisions must be formally approved:

1. **Authentication Architecture Strategy:**
   - *Current State:* FastAPI custom JWT with PBKDF2 hashed passwords in `public.users`.
   - *Future Option:* Complete migration of user identities into Supabase Auth (`auth.users`).
   - *Approval Needed:* Confirmation that LUXE.TECH will maintain FastAPI custom JWT as the primary authentication engine for Phase 15.

2. **Relational User Ownership on `images` Table:**
   - *Current State:* Upload privacy is enforced via user-namespaced storage paths (`storage_path = '{user_id}/{uuid}_{filename}'`). The database table `images` contains 13 columns matching `ImageRecord` without a `user_id` foreign key.
   - *Proposed Evolution:* Adding `user_id VARCHAR REFERENCES public.users(id) ON DELETE SET NULL;`.
   - *Approval Needed:* Confirmation to keep the baseline at 13 columns for exact Day-0 parity, scheduling the relational `user_id` addition for Migration 003.

3. **Remote Environment Introspection Authorization:**
   - *Current State:* All work has been strictly offline. No remote connections have been initiated.
   - *Approval Needed:* Explicit authorization to connect to the dedicated Supabase project to verify that the `public` schema is empty prior to applying the baseline migration.

